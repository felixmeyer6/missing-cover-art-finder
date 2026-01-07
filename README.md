# Cover Art Fixer

A Python script to download and embed missing album artwork into your local music library using the Discogs API.

It ensures all covers are standardized, square JPEGs before being injected into ID3 tags.

| Feature | Description |
| :--- | :--- |
| **Auto-Match** | Rapidly scans and pulls the top result for high-confidence matches. |
| **Manual Mode** | Interactive CLI loop for refining searches and choosing between releases. |
| **Auto-Cropping** | Mathematically centers and crops rectangular art into 1:1 squares. |

## 📦 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/music-library-fixer.git
   cd music-library-fixer
   ```

2. **Install Python dependencies:**
   ```bash
   pip install mutagen requests discogs-client Pillow
   ```

3. **Get a Discogs Token:**
   Generate a personal access token at [discogs.com/settings/developers](https://www.discogs.com/settings/developers).

## 🚀 Quick Start

Before running, open the script and update the configuration variables:

```python
LIBRARY_PATH = "/Users/YourName/Music"
DISCOGS_TOKEN = "your_token_here"
```

### Usage
Run the script to begin the two-phase processing:
```bash
python find-missing-covers.py
```

## 🧠 The Workflow

### 1. 🔍 Metadata Extraction
Uses `mutagen` to extract `artist` and `title` tags. If tags are missing, the file is skipped. It specifically checks for existing `APIC` frames to avoid overwriting existing art.

### 2. 🎛️ Discogs Search Logic
*   **Exact Matching:** Queries the API using specific `artist` and `track` filters.
*   **Manual Refinement:** Performs a broad-string search. It retrieves the top 5 results, extracting the Title, Year, and Label to help you identify the correct release.

### 3. 🖼️ Image Optimization (Pillow)
Once a URL is retrieved, the image is processed in memory:
*   **Aspect Ratio Correction:** Performs a center-crop to ensure a perfect square.
*   **Format Standardization:** Converts `RGBA` or `P` (indexed) modes to `RGB` and exports as JPEG.

### 4. 💉 ID3 Injection
The processed binary data is wrapped in an `APIC` frame with:
*   **Encoding:** 3 (UTF-8)
*   **MIME Type:** image/jpeg
*   **Picture Type:** 3 (Front Cover)

## ⚠️ Limitations

*   **File Format:** This version is specifically for `.mp3` files using ID3v2 tags.
*   **Rate Limits:** Discogs limits requests per minute. The script includes `time.sleep` intervals to stay within "Community" tier limits.
*   **Tag Quality:** The accuracy of the "Auto-Scan" phase depends entirely on the accuracy of your existing Artist and Title tags.
