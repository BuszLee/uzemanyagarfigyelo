from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import math
import re
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

# =====================================================
# CONFIG
# =====================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

CACHE_SECONDS = 300
cache = {}

# =====================================================
# HELPERS
# =====================================================

def haversine(lat1, lon1, lat2, lon2):
    r = 6371.0

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(math.radians(lat1)) *
        math.cos(math.radians(lat2)) *
        math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(r * c, 2)


def detect_brand(name):
    n = name.upper()

    if "OMV" in n:
        return "OMV"
    if "MOL" in n:
        return "MOL"
    if "SHELL" in n:
        return "Shell"
    if "ORLEN" in n:
        return "Orlen"
    if "AVIA" in n:
        return "Avia"

    return "Benzinkút"


def estimate_price(brand):
    prices = {
        "MOL": 667,
        "OMV": 672,
        "Shell": 675,
        "Orlen": 667,
        "Avia": 664,
        "Benzinkút": 665
    }
    return prices.get(brand, 665)


def next_change_day():
    wd = datetime.today().weekday()

    if wd in [0, 1]:
        return "Szerdától"
    elif wd in [2, 3]:
        return "Péntektől"
    else:
        return "Jövő héten"


# =====================================================
# GEOCODE ADDRESS -> COORD
# =====================================================

def geocode(address):

    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": address + ", Hungary",
                "format": "json",
                "limit": 1
            },
            headers=HEADERS,
            timeout=10
        )

        data = r.json()

        if len(data) > 0:
            return (
                float(data[0]["lat"]),
                float(data[0]["lon"])
            )

    except:
        pass

    return None, None


# =====================================================
# REAL STATIONS FROM HOLTANKOLJAK
# =====================================================

def load_real_stations(user_lat, user_lon):

    key = f"{round(user_lat,2)}_{round(user_lon,2)}"

    if key in cache:
        if time.time() - cache[key]["time"] < CACHE_SECONDS:
            return cache[key]["data"]

    try:
        url = "https://holtankoljak.hu"

        r = requests.get(
            url,
            headers=HEADERS,
            timeout=10
        )

        html = r.text

        text = BeautifulSoup(
            html,
            "html.parser"
        ).get_text("\n", strip=True)

        lines = text.split("\n")

        result = []

        for line in lines:

            if len(result) >= 20:
                break

            if any(x in line.upper() for x in [
                "OMV", "MOL", "SHELL", "ORLEN", "AVIA"
            ]):

                nums = re.findall(r'\d{3}', line)

                if len(nums) == 0:
                    continue

                price = int(nums[0])

                name = line[:70].strip()
                brand = detect_brand(name)

                lat, lon = geocode(name)

                if lat is None:
                    continue

                dist = haversine(
                    user_lat,
                    user_lon,
                    lat,
                    lon
                )

                result.append({
                    "name": name,
                    "brand": brand,
                    "fuelType": "95 Benzin",
                    "price": price,
                    "lat": lat,
                    "lon": lon,
                    "distance": dist
                })

        result.sort(
            key=lambda x: x["distance"]
        )

        cache[key] = {
            "time": time.time(),
            "data": result
        }

        return result

    except:
        if key in cache:
            return cache[key]["data"]

        return []


# =====================================================
# RADAR
# =====================================================

def load_radar():

    try:
        r = requests.get(
            "https://holtankoljak.hu/uzemanyag_arvaltozasok",
            timeout=10,
            headers=HEADERS
        )

        txt = BeautifulSoup(
            r.text,
            "html.parser"
        ).get_text(" ", strip=True).lower()

        radar95 = "+0 Ft"
        radarDiesel = "+0 Ft"

        m1 = re.search(
            r'benzin.*?([+-]?\d+)\s*ft',
            txt
        )

        if m1:
            radar95 = f"{m1.group(1)} Ft"

        m2 = re.search(
            r'(gázolaj|diesel).*?([+-]?\d+)\s*ft',
            txt
        )

        if m2:
            radarDiesel = f"{m2.group(2)} Ft"

        return {
            "radarDay": next_change_day(),
            "radar95": radar95,
            "radarDiesel": radarDiesel
        }

    except:
        return {
            "radarDay": next_change_day(),
            "radar95": "+8 Ft",
            "radarDiesel": "+11 Ft"
        }


# =====================================================
# ROUTES
# =====================================================

@app.route("/")
def home():
    return "FINAL HYBRID REAL Backend ONLINE"


@app.route("/stations")
def stations():

    user_lat = float(
        request.args.get("lat", 47.4979)
    )

    user_lon = float(
        request.args.get("lon", 19.0402)
    )

    rows = load_real_stations(
        user_lat,
        user_lon
    )

    prices = [x["price"] for x in rows]

    avg95 = round(sum(prices) / len(prices)) if prices else 0
    avgDiesel = avg95 + 28 if avg95 else 0

    radar = load_radar()

    return jsonify({
        "status": "ok",
        "average95": avg95,
        "averageDiesel": avgDiesel,
        "radarDay": radar["radarDay"],
        "radar95": radar["radar95"],
        "radarDiesel": radar["radarDiesel"],
        "stations": rows
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
