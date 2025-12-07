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
TIMEOUT = 30

# DigimonCard.io rate limit:
# 15 requests per 10 seconds
# We use 1 second delay per request to stay safe
REQUEST_DELAY = 1.0


# -----------------------------
# API FUNCTIONS
# -----------------------------

def fetch_all_cards():
    """
    Fetches the master list of all Digimon Card Game cards.
    """
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
    """
    Fetches full data for a specific card.
    """
    url = f"{API_BASE}/search"
    params = {
        "card": card_number
    }

    response = requests.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()

    return response.json()


# -----------------------------
# MAIN PROCESS
# -----------------------------

def main():
    print("🚀 Starting Digimon TCG data fetch...")

    all_cards = fetch_all_cards()
    total_cards = len(all_cards)

    print(f"✅ Found {total_cards} total cards")

    output = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "total_cards": total_cards,
        "card_list": all_cards,
        "cards": {}
    }

    failed_cards = []

    for index, card in enumerate(all_cards, start=1):
        card_number = (
            card.get("cardnumber")
            or card.get("cardNumber")
            or card.get("id")
        )

        if not card_number:
            continue

        print(f"🔄 [{index}/{total_cards}] Fetching {card_number}...")

        try:
            details = fetch_card_details(card_number)
            output["cards"][card_number] = details

        except Exception as e:
            print(f"❌ Failed to fetch {card_number}: {e}")
            failed_cards.append(card_number)

        # Rate limit safety
        time.sleep(REQUEST_DELAY)

    output["failed_cards"] = failed_cards

    os.makedirs("data", exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("✅ Data saved to:", OUTPUT_FILE)

    if failed_cards:
        print("⚠️ Failed cards:", failed_cards)


# -----------------------------
# ENTRY POINT
# -----------------------------

if __name__ == "__main__":
    main()
