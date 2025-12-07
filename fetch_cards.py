import requests
import json
import os
import time
from datetime import datetime
from collections import deque

# -----------------------------
# CONFIG
# -----------------------------

API_BASE = "https://digimoncard.io/api-public"
OUTPUT_FILE = "data/digimon_cards.json"
IMAGE_DIR = "data/images"
TIMEOUT = 30

# HARD SAFETY LIMITS
MAX_REQUESTS = 10        # max allowed in window
WINDOW_SECONDS = 10     # per 10 seconds
REQUEST_LOG = deque()  # timestamps of recent requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DigimonTCGFetcher/1.0; +https://github.com)"
}

# Toggle image downloading if needed
DOWNLOAD_IMAGES = True   # set to False for data-only mode


# -----------------------------
# HARD RATE LIMITER
# -----------------------------

def wait_for_rate_limit():
    now = time.time()

    # Clear old timestamps
    while REQUEST_LOG and now - REQUEST_LOG[0] > WINDOW_SECONDS:
        REQUEST_LOG.popleft()

    # If we're at the limit, wait
    if len(REQUEST_LOG) >= MAX_REQUESTS:
        sleep_time = WINDOW_SECONDS - (now - REQUEST_LOG[0]) + 0.5
        print(f"⏳ Rate limit reached, sleeping {sleep_time:.1f}s")
        time.sleep(max(sleep_time, 1))

    REQUEST_LOG.append(time.time())


# -----------------------------
# SAFE REQUEST WRAPPER
# -----------------------------

def safe_get(url, params=None):
    wait_for_rate_limit()

    resp = requests.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=TIMEOUT
    )

    if resp.status_code == 429:
        print("🚫 HARD RATE LIMIT HIT — backing off 30s")
        time.sleep(30)
        return safe_get(url, params)

    resp.raise_for_status()
    return resp


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
    resp = safe_get(url, params)

    if resp.status_code == 403:
        raise RuntimeError("🚫 Digimon API is blocking this IP")

    return resp.json()


# -----------------------------
# IMAGE DOWNLOADER
# -----------------------------

def download_image(card_number, image_url, failed_images):
    if not DOWNLOAD_IMAGES or not image_url:
        return

    os.makedirs(IMAGE_DIR, exist_ok=True)
    file_path = os.path.join(IMAGE_DIR, f"{card_number}.jpg")

    if os.path.exists(file_path):
        return

    try:
        print(f"🖼 Downloading image for {card_number}")

        wait_for_rate_limit()
        img = requests.get(image_url, headers=HEADERS, timeout=TIMEOUT)

        if img.status_code == 429:
            print("🚫 Image host limit hit — backing off 30s")
            time.sleep(30)
            return download_image(card_number, image_url, failed_images)

        img.raise_for_status()

        with open(file_path, "wb") as f:
            f.write(img.content)

    except Exception as e:
        print(f"⚠️ Image download failed for {card_number}: {e}")
        failed_images.append(card_number)


# -----------------------------
# MAIN PROCESS (RATE-LIMIT SAFE)
# -----------------------------

def main():
    print("🚀 Starting Digimon TCG HARD-RATE-LIMIT SAFE update...")

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

    print("✅ HARD-SAFE update complete")
    print("🆕 New cards added:", new_cards)
    print("📦 Total stored cards:", existing_data["total_cards"])


# -----------------------------
# ENTRY POINT
# -----------------------------

if __name__ == "__main__":
    main()
