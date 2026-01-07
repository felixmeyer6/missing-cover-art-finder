import os
import time
from io import BytesIO

import discogs_client
import mutagen
import requests
from mutagen.id3 import APIC, ID3
from mutagen.id3 import error as ID3Error
from mutagen.mp3 import MP3
from PIL import Image

# Configuration
LIBRARY_PATH = "/Users/Music"
DISCOGS_TOKEN = "make one at https://www.discogs.com/settings/developers"
USER_AGENT = "MusicLibraryFixer/1.0"


def init_discogs():
    return discogs_client.Client(USER_AGENT, user_token=DISCOGS_TOKEN)


def get_metadata(filepath):
    try:
        audio = mutagen.File(filepath, easy=True)
        if audio:
            artist = audio.get("artist", [None])[0]
            title = audio.get("title", [None])[0]
            return artist, title
    except Exception:
        pass
    return None, None


def has_cover_art(filepath):
    try:
        audio = MP3(filepath, ID3=ID3)
        if audio.tags:
            for key in audio.tags.keys():
                if key.startswith("APIC:"):
                    return True
        return False
    except Exception:
        return False


def search_discogs_auto(client, artist, title):
    try:
        results = client.search(artist=artist, track=title, type="release")
        for r in results:
            if r.images:
                return r.images[0]["uri"]
            break
    except Exception as e:
        print(f"   [!] Auto-search error: {e}")
    return None


def search_discogs_manual(client, query):
    """Broad search returning top 5 results using safe iteration."""
    try:
        results = client.search(query, type="release")
        valid_results = []
        count = 0

        for r in results:
            if count >= 20:
                break
            try:
                if r.images:
                    valid_results.append(r)
            except:
                pass

            if len(valid_results) >= 5:
                break
            count += 1

        return valid_results
    except Exception as e:
        if "429" in str(e):
            print("   [!] Rate limit hit (429). Pausing for 10s...")
            time.sleep(10)
            return search_discogs_manual(client, query)
        print(f"   [!] Search error: {e}")
        return []


def download_and_crop(url):
    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        img = Image.open(BytesIO(response.content))

        width, height = img.size
        if width != height:
            new_size = min(width, height)
            left = (width - new_size) / 2
            top = (height - new_size) / 2
            right = (width + new_size) / 2
            bottom = (height + new_size) / 2
            img = img.crop((left, top, right, bottom))

        output = BytesIO()
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(output, format="JPEG")
        return output.getvalue()
    except Exception as e:
        print(f"   [!] Image error: {e}")
        return None


def embed_art(filepath, image_data):
    try:
        audio = MP3(filepath, ID3=ID3)
        try:
            audio.add_tags()
        except ID3Error:
            pass

        audio.tags.add(
            APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=image_data)
        )
        audio.save()
        print("   -> Art embedded.")
        return True
    except Exception as e:
        print(f"   [!] Embedding error: {e}")
        return False


def manual_process_loop(client, filepath, artist, title):
    print("\n--------------------------------------------------")
    print(f"MANUAL INPUT REQUIRED: {os.path.basename(filepath)}")
    print(f"Current Tags: {artist} - {title}")

    current_query = f"{artist} {title}"

    for trial in range(1, 4):
        print(f"\n[Trial {trial}/3] Searching for: '{current_query}'")
        results = search_discogs_manual(client, current_query)

        if not results:
            print("   -> No results found.")
        else:
            print("   Select a cover:")
            for idx, r in enumerate(results):
                r_title = getattr(r, "title", "Unknown Title")
                r_year = getattr(r, "year", "????")
                label_name = "Unknown Label"
                if hasattr(r, "labels") and r.labels:
                    label_name = r.labels[0].name

                print(f"   [{idx + 1}] {r_title} ({r_year}) - {label_name}")

            print("   [0] None of these (Refine Search)")
            print("   [s] Skip this file entirely")

            choice = input("   > ").strip().lower()

            if choice == "s":
                return

            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(results):
                    selected = results[idx - 1]
                    img_url = selected.images[0]["uri"]
                    print(f"   -> Downloading: {selected.title}...")
                    img_data = download_and_crop(img_url)
                    if img_data:
                        embed_art(filepath, img_data)
                    return

        if trial < 3:
            print("   -> Please type a new search query (e.g., 'Artist Album'):")
            user_input = input("   Query: ").strip()
            if not user_input:
                print("   -> Empty input. Skipping.")
                return
            current_query = user_input
        else:
            print("   -> Max trials reached. Skipping file.")


def main():
    if DISCOGS_TOKEN == "YOUR_DISCOGS_TOKEN":
        print("Please set your Discogs Token.")
        return

    d = init_discogs()
    deferred_files = []

    print(f"--- Phase 1: Auto-Scan {LIBRARY_PATH} ---")

    for root, dirs, files in os.walk(LIBRARY_PATH):
        for file in files:
            if file.lower().endswith(".mp3"):
                filepath = os.path.join(root, file)

                if not has_cover_art(filepath):
                    artist, title = get_metadata(filepath)

                    if artist and title:
                        print(f"[AUTO] Checking: {file}")
                        image_url = search_discogs_auto(d, artist, title)

                        if image_url:
                            print("   -> Match found.")
                            img_data = download_and_crop(image_url)
                            if img_data:
                                embed_art(filepath, img_data)
                            time.sleep(1.1)
                        else:
                            print("   -> No exact match. Deferring.")
                            deferred_files.append((filepath, artist, title))
                    else:
                        print(f"[SKIP] {file} (No tags)")

    if deferred_files:
        print(f"\n\n--- Phase 2: Manual Processing ({len(deferred_files)} files) ---")
        for filepath, artist, title in deferred_files:
            manual_process_loop(d, filepath, artist, title)
            time.sleep(1)
    else:
        print("\nAll missing covers handled automatically!")


if __name__ == "__main__":
    main()
