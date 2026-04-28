from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import math
import re

app = Flask(__name__)
CORS(app)

# ======================================================
# SEGÉDEK
# ======================================================

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

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return round(r * c, 2)


def extract_brand(name: str):
    n = name.lower()

    if "mol" in n:
        return "MOL"
    if "omv" in n:
        return "OMV"
    if "shell" in n:
        return "Shell"
    if "orlen" in n:
        return "Orlen"
    if "lukoil" in n:
        return "Lukoil"

    return "Benzinkút"


# ======================================================
# VALÓS ÁR BECSLÉS
# ======================================================

def scrape_average_price():
    """
    holtankoljak.hu változás oldal alapján
    országos becsült átlag
    """

    try:
        url = "https://holtankoljak.hu/uzemanyag_arvaltozasok"

        html = requests.get(
            url,
            timeout=8,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            }
        ).text

        prices = re.findall(
            r'(\d{3})\s*Ft',
            html
        )

        nums = [
            int(x)
            for x in prices
            if 500 <= int(x) <= 900
        ]

        if nums:
            avg = round(sum(nums) / len(nums))
            return avg

    except:
        pass

    return 667


def estimated_price(brand, avg95):

    diff = {
        "MOL": 0,
        "OMV": 5,
        "Shell": 8,
        "Orlen": -2,
        "Lukoil": -1,
        "Benzinkút": 0
    }

    return avg95 + diff.get(brand, 0)


# ======================================================
# RADAR
# ======================================================

def get_radar():

    try:
        url = "https://holtankoljak.hu/uzemanyag_arvaltozasok"

        html = requests.get(
            url,
            timeout=8,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            }
        ).text.lower()

        if "szerdától" in html:
            day = "Szerdától"
        elif "péntektől" in html:
            day = "Péntektől"
        else:
            day = "Hamarosan"

        up = re.findall(
            r'(\d+)\s*ft.*drág',
            html
        )

        down = re.findall(
            r'(\d+)\s*ft.*csökken',
            html
        )

        if up:
            return f"⚠️ {day} várható drágulás (+{up[0]} Ft)"

        if down:
            return f"📉 {day} várható csökkenés (-{down[0]} Ft)"

    except:
        pass

    return "ℹ️ Nincs friss árváltozás"


# ======================================================
# VALÓS KUTAK OSM-ből
# ======================================================

def fetch_real_stations(lat, lon):

    overpass_url = \
        "https://overpass-api.de/api/interpreter"

    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="fuel"](around:7000,{lat},{lon});
      way["amenity"="fuel"](around:7000,{lat},{lon});
      relation["amenity"="fuel"](around:7000,{lat},{lon});
    );
    out center tags;
    """

    try:
        res = requests.post(
            overpass_url,
            data=query,
            timeout=30,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            }
        )

        data = res.json()

        return data.get(
            "elements",
            []
        )

    except:
        return []


# ======================================================
# API
# ======================================================

@app.route("/stations")
def stations():

    lat = float(
        request.args.get(
            "lat",
            47.4979
        )
    )

    lon = float(
        request.args.get(
            "lon",
            19.0402
        )
    )

    avg95 = scrape_average_price()

    elements = fetch_real_stations(
        lat,
        lon
    )

    result = []

    for item in elements:

        tags = item.get(
            "tags",
            {}
        )

        name = tags.get(
            "name",
            "Benzinkút"
        )

        brand = extract_brand(name)

        if "lat" in item:
            s_lat = item["lat"]
            s_lon = item["lon"]
        else:
            center = item.get(
                "center",
                {}
            )
            s_lat = center.get("lat")
            s_lon = center.get("lon")

        if s_lat is None:
            continue

        distance = haversine(
            lat, lon,
            s_lat, s_lon
        )

        result.append({
            "name": name,
            "brand": brand,
            "fuelType": "95 Benzin",
            "price": estimated_price(
                brand,
                avg95
            ),
            "lat": s_lat,
            "lon": s_lon,
            "distance": distance
        })

    result.sort(
        key=lambda x:
        x["distance"]
    )

    result = result[:30]

    return jsonify({
        "average95": avg95,
        "averageDiesel": avg95 + 30,
        "radar": get_radar(),
        "stations": result
    })


# ======================================================

@app.route("/")
def home():
    return "Radar Plus REAL backend OK"


# ======================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=10000
    )
