import os
import re
import math
import time
import requests

from flask import Flask, jsonify, request
from flask_cors import CORS

# ==================================================
# APP
# ==================================================

app = Flask(__name__)
CORS(app)

# ==================================================
# CONFIG
# ==================================================

API_KEY = os.getenv(
    "GEOAPIFY_KEY",
    "fdfd01a4bf2748849f763d1efee731dd"
)

REQUEST_TIMEOUT = 12
SEARCH_RADIUS_M = 7000
SEARCH_LIMIT = 30
CACHE_SECONDS = 300

# ==================================================
# CACHE
# ==================================================

fuel_cache = {
    "time": 0,
    "data": None
}

# ==================================================
# HELPERS
# ==================================================

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

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return round(r * c, 2)


# ==================================================
# BRAND DETECT
# ==================================================

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
        "avia": "AVIA",
        "agip": "AGIP",
        "eni": "ENI",
        "mpetrol": "MPETROL",
        "fullenergy": "FULLENERGY",
        "full energy": "FULLENERGY",
        "tesco": "TESCO",
        "auchan": "AUCHAN"
    }

    for key, value in brands.items():
        if key in n:
            return value

    return "Benzinkút"


# ==================================================
# PRICE ESTIMATE
# ==================================================

def estimate_station_price(avg95, brand):
    plus = {
        "OMV": 6,
        "SHELL": 8,
        "MOL": 3,
        "ORLEN": 2,
        "LUKOIL": 1,
        "TESCO": -4,
        "AUCHAN": -5,
        "FULLENERGY": 0,
        "MPETROL": 0
    }.get(brand, 0)

    return avg95 + plus


# ==================================================
# DAY DETECT
# ==================================================

def detect_day(text):
    days = [
        "hétfőtől",
        "keddtől",
        "szerdától",
        "csütörtöktől",
        "péntektől",
        "szombattól",
        "vasárnaptól"
    ]

    for d in days:
        if d in text:
            return d.capitalize()

    # fallback: holnap / ma
    if "holnaptól" in text:
        return "Holnaptól"

    if "mától" in text:
        return "Mától"

    return "Hamarosan"


# ==================================================
# CHANGE DETECT
# ==================================================

def detect_change(text, fuel_words):
    """
    pozitív / negatív változás keresés
    """

    for word in fuel_words:

        pattern = (
            rf"{word}.{{0,120}}?"
            rf"(\d+)[ -]?(?:forint|ft)"
        )

        m = re.search(
            pattern,
            text,
            re.S
        )

        if m:
            value = m.group(1)

            if any(x in text for x in [
                "csökken",
                "mérséklődik",
                "olcsóbb"
            ]):
                return f"-{value} Ft"

            return f"+{value} Ft"

    return "0 Ft"


# ==================================================
# TREND DETECT
# ==================================================

def detect_trend(text):
    if any(x in text for x in [
        "csökken",
        "mérséklődik",
        "olcsóbb"
    ]):
        return "csökkenés"

    if any(x in text for x in [
        "emelkedik",
        "drágul",
        "nő",
        "ármelkedés",
        "áremelkedés"
    ]):
        return "drágulás"

    return "változás"


# ==================================================
# FUEL SCRAPER FINAL
# ==================================================

def get_fuel_info():
    now = time.time()

    if (
        fuel_cache["data"]
        and now - fuel_cache["time"] < CACHE_SECONDS
    ):
        return fuel_cache["data"]

    average95 = 680
    averageDiesel = 714

    radarDay = "Hamarosan"
    radar95 = "0 Ft"
    radarDiesel = "0 Ft"
    radarTrend = "változás"

    try:
        url = (
            "https://holtankoljak.hu/"
            "uzemanyag_arvaltozasok"
        )

        r = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            }
        )

        r.encoding = "utf-8"

        text = r.text.lower()

        # -------------------------
        # ÁTLAGÁR
        # -------------------------

        m95 = re.search(
            r"95.*?(\d{3})\s*ft",
            text,
            re.S
        )

        md = re.search(
            r"gázolaj.*?(\d{3})\s*ft",
            text,
            re.S
        )

        if m95:
            average95 = int(m95.group(1))

        if md:
            averageDiesel = int(md.group(1))

        # -------------------------
        # RADAR
        # -------------------------

        radarDay = detect_day(text)

        radar95 = detect_change(
            text,
            ["benzin", "95"]
        )

        radarDiesel = detect_change(
            text,
            ["gázolaj", "diesel"]
        )

        radarTrend = detect_trend(text)

    except Exception as e:
        print("SCRAPER ERROR:", e)

    result = {
        "average95": average95,
        "averageDiesel": averageDiesel,
        "radarDay": radarDay,
        "radar95": radar95,
        "radarDiesel": radarDiesel,
        "radarTrend": radarTrend
    }

    fuel_cache["time"] = now
    fuel_cache["data"] = result

    return result


# ==================================================
# HOME
# ==================================================

@app.route("/")
def home():
    return "UZEMANYAGARFIGYELO API ONLINE"


# ==================================================
# STATIONS
# ==================================================

@app.route("/stations")
def stations():
    lat = request.args.get(
        "lat",
        default=47.4979,
        type=float
    )

    lon = request.args.get(
        "lon",
        default=19.0402,
        type=float
    )

    fuel = get_fuel_info()

    geo_url = (
        "https://api.geoapify.com/v2/places"
        f"?categories=service.vehicle.fuel"
        f"&filter=circle:{lon},{lat},{SEARCH_RADIUS_M}"
        f"&limit={SEARCH_LIMIT}"
        f"&apiKey={API_KEY}"
    )

    output = []

    try:
        r = requests.get(
            geo_url,
            timeout=REQUEST_TIMEOUT
        )

        data = r.json()

        for item in data.get(
            "features",
            []
        ):
            p = item.get(
                "properties",
                {}
            )

            s_lat = p.get("lat")
            s_lon = p.get("lon")

            if not s_lat or not s_lon:
                continue

            raw_name = p.get(
                "name",
                "Benzinkút"
            )

            brand = detect_brand(
                raw_name
            )

            address = (
                p.get("formatted")
                or p.get("address_line2")
                or p.get("address_line1")
                or "Ismeretlen cím"
            )

            dist = haversine_km(
                lat,
                lon,
                s_lat,
                s_lon
            )

            output.append({
                "name":
                    f"{brand}, {address}",
                "brand":
                    brand,
                "fuelType":
                    "95 Benzin",
                "price":
                    estimate_station_price(
                        fuel["average95"],
                        brand
                    ),
                "lat":
                    s_lat,
                "lon":
                    s_lon,
                "distance":
                    dist
            })

        output.sort(
            key=lambda x:
            x["distance"]
        )

        return jsonify({
            "status": "ok",

            "average95":
                fuel["average95"],

            "averageDiesel":
                fuel["averageDiesel"],

            "radarDay":
                fuel["radarDay"],

            "radar95":
                fuel["radar95"],

            "radarDiesel":
                fuel["radarDiesel"],

            "radarTrend":
                fuel["radarTrend"],

            "stations":
                output
        })

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e),

            "average95":
                fuel["average95"],

            "averageDiesel":
                fuel["averageDiesel"],

            "radarDay":
                fuel["radarDay"],

            "radar95":
                fuel["radar95"],

            "radarDiesel":
                fuel["radarDiesel"],

            "radarTrend":
                fuel["radarTrend"],

            "stations": []
        })


# ==================================================
# MAIN
# ==================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        )
    )
