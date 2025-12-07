# Digimon TCG Auto-Fetcher

This project automatically downloads and archives the full Digimon Card Game database using the public DigimonCard.io API.

The data is stored as a structured JSON file and refreshes automatically every week using GitHub Actions.

---

## Features

- Automatically pulls full Digimon card data
- Weekly auto-updates via GitHub Actions
- Safe API rate-limiting with request delays
- Clean JSON storage with timestamps
- Fully open-source and customizable

---

## Setup (Local Use)

### 1. Install Python 3.10+
https://www.python.org/downloads/

### 2. Install Dependencies

```bash
pip install -r requirements.txt
