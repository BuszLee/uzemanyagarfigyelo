import os
import re
import math
import time
import requests

from flask import Flask, jsonify, request
from flask_cors import CORS

# --------------------------------------------------
# APP
# --------------------------------------------------

app = Flask(__name__)
CORS(app)

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

API_KEY = os.getenv("GEOAPIFY_KEY", "fdfd01a4bf2748849f763d1efee731dd")

REQUEST_TIMEOUT = 12
SEARCH_RADIUS_M = 7000
SEARCH_LIMIT = 30
CACHE_SECONDS = 300

# --------------------------------------------------
# CACHE
# --------------------------------------------------

fuel_cache = {
    "time": 0,
    "data": None
}

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0

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


def detect_brand(name):
    if not name:
        return "Benzinkút"

    n = name.lower()

    brands = {
        "mol": "MOL",
        "omv": "OMV",
        "shell": "SHELL",
        "lukoil": "LUKOIL",
        "orlen": "ORLEN",
        "avia": "AVIA",
        "eni": "ENI",
        "agip": "AGIP",
        "auchan": "AUCHAN",
        "tesco": "TESCO",
        "fullenergy": "FULLENERGY"
    }

    for key, value in brands.items():
        if key in n:
            return value

    return "Benzinkút"


def estimate_station_price(avg95, brand):
    extra = {
        "OMV": 6,
        "SHELL": 8,
        "MOL": 3,
        "AUCHAN": -5,
        "TESCO": -4,
        "ORLEN": 2,
        "LUKOIL": 1,
        "FULLENERGY": 0
    }.get(brand, 0)

    return avg95 + extra


# --------------------------------------------------
# SCRAPER (FIXED)
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
        url = "https://holtankoljak.hu/uzemanyag_arvaltozasok"

        r = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        r.encoding = "utf-8"
        text = r.text.lower()

        # ----------------------------------
        # ÁTLAG ÁRAK
        # ----------------------------------
        avg_b = re.search(r"95.*?(\d{3})\s*ft", text)
        avg_d = re.search(r"gázolaj.*?(\d{3})\s*ft", text)

        if avg_b:
            average95 = int(avg_b.group(1))

        if avg_d:
            averageDiesel = int(avg_d.group(1))

        # ----------------------------------
        # NAP (csütörtöktől stb.)
        # ----------------------------------
        day_match = re.search(
            r"(hétfőtől|keddtől|szerdától|csütörtöktől|péntektől|szombattól|vasárnaptól)",
            text
        )

        if day_match:
            radarDay = day_match.group(1).capitalize()

        # ----------------------------------
        # VÁLTOZÁS (FIX BUG!!!)
        # csak "nő/csökken" UTÁNI szám
        # ----------------------------------

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
# ROUTES
# --------------------------------------------------

@app.route("/")
def home():
    return "UZEMANYAGARFIGYELO API ONLINE"


@app.route("/stations")
def stations():
    lat = request.args.get("lat", default=47.4979, type=float)
    lon = request.args.get("lon", default=19.0402, type=float)

    fuel = get_fuel_info()

    url = (
        "https://api.geoapify.com/v2/places"
        f"?categories=service.vehicle.fuel"
        f"&filter=circle:{lon},{lat},{SEARCH_RADIUS_M}"
        f"&limit={SEARCH_LIMIT}"
        f"&apiKey={API_KEY}"
    )

    stations = []

    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        data = r.json()

        for item in data.get("features", []):
            p = item.get("properties", {})

            station_lat = p.get("lat")
            station_lon = p.get("lon")

            if station_lat is None or station_lon is None:
                continue

            raw_name = p.get("name", "Benzinkút")
            brand = detect_brand(raw_name)

            address = (
                p.get("formatted")
                or p.get("address_line2")
                or p.get("address_line1")
                or "Ismeretlen cím"
            )

            distance_km = haversine_km(
                lat, lon,
                station_lat, station_lon
            )

            stations.append({
                "name": f"{brand}, {address}",
                "brand": brand,
                "fuelType": "95 Benzin",
                "price": estimate_station_price(
                    fuel["average95"],
                    brand
                ),
                "lat": station_lat,
                "lon": station_lon,
                "distance": distance_km
            })

        stations.sort(key=lambda x: x["distance"])

        return jsonify({
            "status": "ok",
            "average95": fuel["average95"],
            "averageDiesel": fuel["averageDiesel"],
            "radarDay": fuel["radarDay"],
            "radar95": fuel["radar95"],
            "radarDiesel": fuel["radarDiesel"],
            "stations": stations
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "average95": fuel["average95"],
            "averageDiesel": fuel["averageDiesel"],
            "radarDay": fuel["radarDay"],
            "radar95": fuel["radar95"],
            "radarDiesel": fuel["radarDiesel"],
            "stations": []
        })


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
