import requests
from bs4 import BeautifulSoup
import json

URL = "https://holtankoljak.hu/station_result"


def get_prices():
    """
    Lekéri a Holtankoljak oldalát és visszaadja
    a kutak adatait listában.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0 Safari/537.36"
        )
    }

    response = requests.get(URL, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    stations = []

    for card in soup.find_all("div", class_="d-flex mb-3"):

        try:

            # márkanév
            brand = ""

            logo = card.find("img", title=True)
            if logo:
                brand = logo["title"].strip()

            # cím
            address = ""

            for a in card.find_all("a"):
                txt = a.get_text(" ", strip=True)

                if "," in txt and len(txt) > 8:
                    address = txt
                    break

            # ár
            price = None

            price_tag = card.find("span", class_="ar")
            if price_tag:
                text = price_tag.get_text(strip=True)

                text = (
                    text.replace("/ liter", "")
                        .replace(",", ".")
                        .strip()
                )

                price = float(text)

            # dátum
            date = ""

            badge = card.find("span", class_="badge")
            if badge:
                date = badge.get_text(strip=True)

            if brand and address and price:

                stations.append({
                    "brand": brand,
                    "address": address,
                    "price": price,
                    "date": date
                })

        except Exception:
            pass

    return stations


def save_to_json(data, filename="prices.json"):

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


if __name__ == "__main__":

    stations = get_prices()

    print(f"\nTalált kutak: {len(stations)}\n")

    for s in stations:

        print(
            f"{s['brand']:10}"
            f"{s['price']:6.1f} Ft   "
            f"{s['address']}"
        )

    save_to_json(stations)

    print("\nprices.json elkészült.")
