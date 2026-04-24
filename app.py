from flask import Flask, jsonify, request
import requests
import math
import json
import os

app = Flask(__name__)

# -------------------------------------------------
# Árak betöltése (ha van prices.json)
# -------------------------------------------------
def load_prices():
    if os.path.exists("prices.json"):
        with open("prices.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

prices = load_prices()

# -------------------------------------------------
# Távolság számítás km
# -------------------------------------------------
def distance_km(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2) * 111

# -------------------------------------------------
# Márka felismerés
# -------------------------------------------------
def detect_brand(name):
    n = name.lower()

    if "shell" in n:
        return "Shell"
    elif "mol" in n:
        return "MOL"
    elif "omv" in n:
        return "OMV"
    elif "lukoil" in n:
        return "Lukoil"
    elif "orlen" in n:
        return "Orlen"
    elif "avia" in n:
        return "Avia"
    else:
        return "Benzinkút"

# -------------------------------------------------
# Főoldal
# -------------------------------------------------
@app.route("/")
def home():
    return "API működik"

# -------------------------------------------------
# Overpass lekérés több szerverrel
# -------------------------------------------------
def get_overpass_data(query):

    urls = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter"
    ]

    for url in urls:
        try:
            r = requests.post(url, data=query, timeout=20)

            if r.status_code == 200:
                return r.json()

        except:
            pass

    return None

# -------------------------------------------------
# Kutak
# -------------------------------------------------
@app.route("/stations")
def stations():

    lat = request.args.get("lat", default=47.4979, type=float)
    lon = request.args.get("lon", default=19.0402, type=float)

    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="fuel"](around:8000,{lat},{lon});
      way["amenity"="fuel"](around:8000,{lat},{lon});
      relation["amenity"="fuel"](around:8000,{lat},{lon});
    );
    out center tags;
    """

    try:
        data = get_overpass_data(query)

        if data is None:
            return jsonify({
                "error": "Nem elérhető térképszerver",
                "stations": []
            })

        stations = []

        for item in data["elements"]:

            tags = item.get("tags", {})

            name = tags.get("name", "Benzinkút")
            street = tags.get("addr:street", "")
            number = tags.get("addr:housenumber", "")

            full_name = name

            if street:
                full_name += ", " + street

            if number:
                full_name += " " + number

            item_lat = item.get("lat")
            item_lon = item.get("lon")

            if item_lat is None:
                item_lat = item.get("center", {}).get("lat")

            if item_lon is None:
                item_lon = item.get("center", {}).get("lon")

            if item_lat is None or item_lon is None:
                continue

            dist = distance_km(lat, lon, item_lat, item_lon)

            brand = detect_brand(name)

            # ár márka alapján
            price = prices.get(brand, 0)

            stations.append({
                "name": full_name,
                "brand": brand,
                "fuelType": "95 Benzin",
                "price": price,
                "lat": item_lat,
                "lon": item_lon,
                "distance": dist
            })

        stations.sort(key=lambda x: x["distance"])

        return jsonify({
            "stations": stations[:20]
        })

    except Exception as e:
        return jsonify({
            "error": str(e),
            "stations": []
        })

# -------------------------------------------------
# Indítás
# -------------------------------------------------
if __name__ == "__main__":
    app.run()
