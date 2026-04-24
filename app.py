from flask import Flask, jsonify, request
import requests
import math
import json
import os

app = Flask(__name__)

# ---------------------------------------------------
# Ár adatbázis betöltés
# ---------------------------------------------------
def load_prices():
    if os.path.exists("prices.json"):
        with open("prices.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

prices = load_prices()

# ---------------------------------------------------
# Távolság km
# ---------------------------------------------------
def distance_km(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1-lat2)**2 + (lon1-lon2)**2) * 111

# ---------------------------------------------------
# Kút márka felismerés
# ---------------------------------------------------
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

# ---------------------------------------------------
# Főoldal
# ---------------------------------------------------
@app.route("/")
def home():
    return "API működik"

# ---------------------------------------------------
# Kutak
# ---------------------------------------------------
@app.route("/stations")
def stations():

    lat = request.args.get("lat", default=47.4979, type=float)
    lon = request.args.get("lon", default=19.0402, type=float)

    query = f"""
    [out:json];
    (
      node["amenity"="fuel"](around:8000,{lat},{lon});
      way["amenity"="fuel"](around:8000,{lat},{lon});
      relation["amenity"="fuel"](around:8000,{lat},{lon});
    );
    out center tags;
    """

    url = "https://overpass-api.de/api/interpreter"

    try:
        r = requests.post(url, data=query, timeout=20)
        data = r.json()

        stations = []

        for item in data["elements"]:

            tags = item.get("tags", {})

            name = tags.get("name", "Benzinkút")
            addr = tags.get("addr:street", "")
            number = tags.get("addr:housenumber", "")

            full_name = name
            if addr:
                full_name += f", {addr}"
            if number:
                full_name += f" {number}"

            item_lat = item.get("lat") or item.get("center", {}).get("lat")
            item_lon = item.get("lon") or item.get("center", {}).get("lon")

            if item_lat is None or item_lon is None:
                continue

            dist = distance_km(lat, lon, item_lat, item_lon)

            price = prices.get(name, 0)

            stations.append({
                "name": full_name,
                "brand": detect_brand(name),
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

if __name__ == "__main__":
    app.run()
