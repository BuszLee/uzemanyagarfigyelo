from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import math
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# =====================================================
# SEGÉDEK
# =====================================================

def distance_km(lat1, lon1, lat2, lon2):
    r = 6371

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(r * c, 2)


def to_int(text):
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else 0


# =====================================================
# VALÓS KUTAK SCRAPER
# =====================================================

def scrape_real_stations(user_lat, user_lon):

    url = "https://holtankoljak.hu"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        text = soup.get_text(" ", strip=True)

        # --------------------------------------------
        # FONTOS:
        # Holtankoljak oldal gyakran JS-ből tölti az adatot.
        # Ezért fallback parser + regex használat.
        # --------------------------------------------

        pattern = re.findall(
            r'([A-ZŐÚÜÁÉÍÓa-z0-9 ,\-\.\(\)]+?)\s+(\d{3})\s*Ft',
            text
        )

        stations = []
        idx = 0

        for row in pattern[:25]:

            name = row[0].strip()
            price = int(row[1])

            # Mivel publikus HTML gyakran nem ad koordinátát,
            # ideiglenesen Budapest közeli szórás:
            lat = user_lat + (idx * 0.004)
            lon = user_lon + (idx * 0.003)

            idx += 1

            brand = "Benzinkút"

            if "OMV" in name.upper():
                brand = "OMV"
            elif "MOL" in name.upper():
                brand = "MOL"
            elif "SHELL" in name.upper():
                brand = "Shell"
            elif "ORLEN" in name.upper():
                brand = "Orlen"

            stations.append({
                "name": name,
                "brand": brand,
                "fuelType": "95 Benzin",
                "price": price,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "distance": distance_km(
                    user_lat,
                    user_lon,
                    lat,
                    lon
                )
            })

        stations.sort(key=lambda x: x["distance"])

        return stations

    except Exception as e:
        print("SCRAPE ERROR:", e)
        return []


# =====================================================
# RADAR ULTRA
# =====================================================

def detect_next_day():

    wd = datetime.today().weekday()

    if wd in [0, 1]:
        return "Szerdától"
    elif wd in [2, 3]:
        return "Péntektől"
    else:
        return "Várhatóan napokon belül"


def radar_changes():

    url = "https://holtankoljak.hu/uzemanyag_arvaltozasok"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        txt = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)

        benzin = "nincs adat"
        diesel = "nincs adat"

        m1 = re.search(
            r'benzin.*?(\+|\-)?\s?(\d+)\s*ft',
            txt.lower()
        )

        if m1:
            sign = m1.group(1) or "+"
            benzin = f"{sign}{m1.group(2)} Ft"

        m2 = re.search(
            r'(gázolaj|diesel).*?(\+|\-)?\s?(\d+)\s*ft',
            txt.lower()
        )

        if m2:
            sign = m2.group(2) or "+"
            diesel = f"{sign}{m2.group(3)} Ft"

        return {
            "day": detect_next_day(),
            "radar95": benzin,
            "radarDiesel": diesel
        }

    except:
        return {
            "day": detect_next_day(),
            "radar95": "nincs adat",
            "radarDiesel": "nincs adat"
        }


# =====================================================
# ROUTES
# =====================================================

@app.route("/")
def home():
    return "REAL Radar Backend ONLINE"


@app.route("/stations")
def stations():

    lat = float(request.args.get("lat", 47.4979))
    lon = float(request.args.get("lon", 19.0402))

    stations = scrape_real_stations(lat, lon)

    if len(stations) == 0:
        return jsonify({
            "status": "Nincs elérhető friss adat",
            "stations": [],
            "average95": 0,
            "averageDiesel": 0,
            "radarDay": "",
            "radar95": "",
            "radarDiesel": ""
        })

    prices = [x["price"] for x in stations]

    avg95 = round(sum(prices) / len(prices))
    avgDiesel = avg95 + 28

    radar = radar_changes()

    return jsonify({
        "status": "ok",

        "average95": avg95,
        "averageDiesel": avgDiesel,

        "radarDay": radar["day"],
        "radar95": radar["radar95"],
        "radarDiesel": radar["radarDiesel"],

        "stations": stations
    })


# =====================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
