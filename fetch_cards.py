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

# API rate limit safety:
REQUEST_DELAY = 1.0  # 1 second per request


# -----------------------------
# LOAD EXISTING DATA
# -----------------------------

def load_existing_data():
    if not os.path.exists(OUTPUT_FILE):
        return {
            "last_updated": None,
            "total_cards": 0,
            "card_list": [],
            "cards": {},
            "failed_cards": []
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
        "sortdirection": "asc",
        "series": "Digimon Card Game"
    }

    print("📡 Fetching master card list...")
    response = requests.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_card_details(card_number):
    url = f"{API_BASE}/search"
    params = {"card": card_number}

    response = requests.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def download_image(card_number, image_url):
    if not image_url:
        return

    os.makedirs(IMAGE_DIR, exist_ok=True)
    file_path = os.path.join(IMAGE_DIR, f"{card_number}.jpg")

    # Skip if already downloaded
    if os.path.exists(file_path):
        return

    try:
        print(f"🖼 Downloading image for {card_number}")
        img = requests.get(image_url, timeout=TIMEOUT)
        img.raise_for_status()

        with open(file_path, "wb") as f:
            f.write(img.content)

    except Exception as e:
        print(f"⚠️ Image download failed for {card_number}: {e}")


# -----------------------------
# MAIN PROCESS
# -----------------------------

def main():
    print("🚀 Starting Digimon TCG incremental update...")

    existing_data = load_existing_data()
    known_cards = set(existing_data["cards"].keys())

    all_cards = fetch_all_cards()
    total_api_cards = len(all_cards)

    new_cards_found = 0
    failed_cards = existing_data.get("failed_cards", [])

    for index, card in enumerate(all_cards, start=1):
        card_number = (
            card.get("cardnumber")
            or card.get("cardNumber")
            or card.get("id")
        )

        if not card_number or card_number in known_cards:
            continue

        print(f"🆕 [{index}/{total_api_cards}] NEW CARD: {card_number}")

        try:
            details = fetch_card_details(card_number)
            existing_data["cards"][card_number] = details
            new_cards_found += 1

            # Try to get image URL from the API result
            if isinstance(details, list) and len(details) > 0:
                image_url = details[0].get("image_url") or details[0].get("imageUrl")
                download_image(card_number, image_url)

        except Exception as e:
            print(f"❌ Failed to fetch {card_number}: {e}")
            failed_cards.append(card_number)

        time.sleep(REQUEST_DELAY)

    # Update metadata
    existing_data["card_list"] = all_cards
    existing_data["total_cards"] = len(existing_data["cards"])
    existing_data["last_updated"] = datetime.utcnow().isoformat() + "Z"
    existing_data["failed_cards"] = failed_cards

    os.makedirs("data", exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

    print("✅ Update complete")
    print("🆕 New cards added:", new_cards_found)
    print("📦 Total stored cards:", existing_data["total_cards"])


# -----------------------------
# ENTRY POINT
# -----------------------------

if __name__ == "__main__":
    main()
