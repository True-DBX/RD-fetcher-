import requests
import json
import os
import time
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------

API_BASE = "https://digimoncard.io/api-public"
OUTPUT_FILE = "data/digimon_cards.json"
IMAGE_DIR = "data/images"
TIMEOUT = 30

# VERY conservative delay
REQUEST_DELAY = 2.5  # seconds between image downloads

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DigimonTCGFetcher/1.0; +https://github.com)"
}

# -----------------------------
# LOAD EXISTING DATA
# -----------------------------

def load_existing_data():
    if not os.path.exists(OUTPUT_FILE):
        return {
            "last_updated": None,
            "total_cards": 0,
            "cards": {},
            "failed_images": []
        }

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# -----------------------------
# API FUNCTIONS
# -----------------------------

def fetch_all_cards():
    url = f"{API_BASE}/getAllCards"
    params = {
        "sort": "name",
        "sortdirection": "asc"
    }

    print("📡 Fetching master card list...")
    resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)

    if resp.status_code == 403:
        raise RuntimeError("🚫 Digimon API is blocking this IP")

    resp.raise_for_status()
    return resp.json()

# -----------------------------
# IMAGE DOWNLOADER
# -----------------------------

def download_image(card_number, image_url, failed_images):
    if not image_url:
        return

    os.makedirs(IMAGE_DIR, exist_ok=True)
    file_path = os.path.join(IMAGE_DIR, f"{card_number}.jpg")

    if os.path.exists(file_path):
        return

    try:
        print(f"🖼 Downloading image for {card_number}")
        img = requests.get(image_url, headers=HEADERS, timeout=TIMEOUT)
        img.raise_for_status()

        with open(file_path, "wb") as f:
            f.write(img.content)

        time.sleep(REQUEST_DELAY)

    except Exception as e:
        print(f"⚠️ Image download failed for {card_number}: {e}")
        failed_images.append(card_number)

# -----------------------------
# MAIN PROCESS (SAFE MODE)
# -----------------------------

def main():
    print("🚀 Starting Digimon TCG SAFE incremental update...")

    os.makedirs("data", exist_ok=True)
    os.makedirs("data/images", exist_ok=True)

    existing_data = load_existing_data()
    known_cards = set(existing_data["cards"].keys())

    all_cards = fetch_all_cards()

    new_cards = 0
    failed_images = existing_data.get("failed_images", [])

    for card in all_cards:
        card_number = (
            card.get("cardnumber")
            or card.get("cardNumber")
            or card.get("id")
        )

        if not card_number or card_number in known_cards:
            continue

        existing_data["cards"][card_number] = card
        new_cards += 1

        # Image field varies by API version
        image_url = (
            card.get("image_url")
            or card.get("imageUrl")
            or card.get("image")
        )

        download_image(card_number, image_url, failed_images)

    existing_data["total_cards"] = len(existing_data["cards"])
    existing_data["last_updated"] = datetime.utcnow().isoformat() + "Z"
    existing_data["failed_images"] = failed_images

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

    print("✅ SAFE update complete")
    print("🆕 New cards added:", new_cards)
    print("📦 Total stored cards:", existing_data["total_cards"])

# -----------------------------
# ENTRY POINT
# -----------------------------

if __name__ == "__main__":
    main()
