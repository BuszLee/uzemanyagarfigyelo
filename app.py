import os
import re
import math
import time
import requests

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

API_KEY = os.getenv("GEOAPIFY_KEY", "fdfd01a4bf2748849f763d1efee731dd")

REQUEST_TIMEOUT = 12
SEARCH_RADIUS_M = 7000
SEARCH_LIMIT = 30
CACHE_SECONDS = 300

fuel_cache = {"time": 0, "data": None}

# --------------------------------------------------

def haversine_km(lat1, lon1, lat2, lon2):
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

# --------------------------------------------------

def detect_brand(name):
    if not name:
        return "Benzinkút"

    n = name.lower()

    brands = {
        "mol": "MOL",
        "omv": "OMV",
        "shell": "SHELL",
        "orlen": "ORLEN",
        "lukoil": "LUKOIL",
        "fullenergy": "FULLENERGY"
    }

    for key, value in brands.items():
        if key in n:
            return value

    return "Benzinkút"

# --------------------------------------------------

def estimate_station_price(avg95, brand):
    extra = {
        "OMV": 6,
        "SHELL": 8,
        "MOL": 3,
        "ORLEN": 2,
        "LUKOIL": 1,
        "FULLENERGY": 0
    }.get(brand, 0)

    return avg95 + extra

# --------------------------------------------------

def get_fuel_info():
    now = time.time()

    if fuel_cache["data"] and now - fuel_cache["time"] < CACHE_SECONDS:
        return fuel_cache["data"]

    average95 = 680
    averageDiesel = 714
    radarDay = "Hamarosan"
    radar95 = "0 Ft"
    radarDiesel = "0 Ft"

    try:
        r = requests.get(
            "https://holtankoljak.hu/uzemanyag_arvaltozasok",
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        text = r.text.lower()

        avg_b = re.search(r"95.*?(\d{3})\s*ft", text)
        avg_d = re.search(r"gázolaj.*?(\d{3})\s*ft", text)

        if avg_b:
            average95 = int(avg_b.group(1))
        if avg_d:
            averageDiesel = int(avg_d.group(1))

        day = re.search(
            r"(hétfőtől|keddtől|szerdától|csütörtöktől|péntektől)",
            text
        )

        if day:
            radarDay = day.group(1).capitalize()

        benzin = re.search(
            r"benzin[^.]*?(nő|csökken)[^.]*?(\d+)\s*forint",
            text
        )

        diesel = re.search(
            r"(gázolaj|diesel)[^.]*?(nő|csökken)[^.]*?(\d+)\s*forint",
            text
        )

        if benzin:
            radar95 = f"+{benzin.group(2)} Ft"

        if diesel:
            radarDiesel = f"+{diesel.group(3)} Ft"

    except Exception as e:
        print("SCRAPER ERROR:", e)

    result = {
        "average95": average95,
        "averageDiesel": averageDiesel,
        "radarDay": radarDay,
        "radar95": radar95,
        "radarDiesel": radarDiesel
    }

    fuel_cache["time"] = now
    fuel_cache["data"] = result

    return result

# --------------------------------------------------

@app.route("/stations")
def stations():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)

    fuel = get_fuel_info()

    url = (
        f"https://api.geoapify.com/v2/places"
        f"?categories=service.vehicle.fuel"
        f"&filter=circle:{lon},{lat},{SEARCH_RADIUS_M}"
        f"&limit={SEARCH_LIMIT}"
        f"&apiKey={API_KEY}"
    )

    stations = []

    r = requests.get(url, timeout=REQUEST_TIMEOUT)
    data = r.json()

    for item in data.get("features", []):
        p = item.get("properties", {})

        s_lat = p.get("lat")
        s_lon = p.get("lon")

        if not s_lat or not s_lon:
            continue

        name = p.get("name", "Benzinkút")
        brand = detect_brand(name)

        address = p.get("formatted", "Ismeretlen cím")

        opening = p.get("opening_hours", "")

        dist = haversine_km(lat, lon, s_lat, s_lon)

        stations.append({
            "name": f"{address}",
            "brand": brand,
            "fuelType": "95 Benzin",
            "price": estimate_station_price(
                fuel["average95"],
                brand
            ),
            "lat": s_lat,
            "lon": s_lon,
            "distance": dist,
            "openingHours": opening
        })

    stations.sort(key=lambda x: x["distance"])

    return jsonify({
        "average95": fuel["average95"],
        "averageDiesel": fuel["averageDiesel"],
        "radarDay": fuel["radarDay"],
        "radar95": fuel["radar95"],
        "radarDiesel": fuel["radarDiesel"],
        "stations": stations
    })
