from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import math
import time
import re
from bs4 import BeautifulSoup
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
    if "LUKOIL" in n:
        return "Lukoil"

    return "Benzinkút"


def estimate_price(brand):
    prices = {
        "MOL": 667,
        "OMV": 672,
        "Shell": 675,
        "Orlen": 667,
        "Avia": 664,
        "Lukoil": 666,
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
# REAL GPS STATIONS (OSM)
# =====================================================

def load_nearby_stations(user_lat, user_lon):

    key = f"{round(user_lat,3)}_{round(user_lon,3)}"

    if key in cache:
        if time.time() - cache[key]["time"] < CACHE_SECONDS:
            return cache[key]["data"]

    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="fuel"](around:10000,{user_lat},{user_lon});
      way["amenity"="fuel"](around:10000,{user_lat},{user_lon});
      relation["amenity"="fuel"](around:10000,{user_lat},{user_lon});
    );
    out center;
    """

    try:
        r = requests.get(
            "https://overpass-api.de/api/interpreter",
            params={"data": query},
            timeout=25,
            headers=HEADERS
        )

        data = r.json()

        result = []

        for item in data["elements"]:

            tags = item.get("tags", {})

            name = tags.get("name", "Benzinkút")

            lat = item.get("lat")
            lon = item.get("lon")

            if lat is None:
                center = item.get("center", {})
                lat = center.get("lat")
                lon = center.get("lon")

            if lat is None or lon is None:
                continue

            brand = detect_brand(name)

            result.append({
                "name": name,
                "brand": brand,
                "fuelType": "95 Benzin",
                "price": estimate_price(brand),
                "lat": lat,
                "lon": lon,
                "distance": haversine(
                    user_lat,
                    user_lon,
                    lat,
                    lon
                )
            })

        result.sort(key=lambda x: x["distance"])
        result = result[:25]

        cache[key] = {
            "time": time.time(),
            "data": result
        }

        return result

    except:
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
    return "GPS REAL Backend ONLINE"


@app.route("/stations")
def stations():

    user_lat = float(
        request.args.get("lat", 47.4979)
    )

    user_lon = float(
        request.args.get("lon", 19.0402)
    )

    rows = load_nearby_stations(
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
