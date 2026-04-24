from flask import Flask, jsonify, request
import requests
import math
import re
from datetime import datetime

app = Flask(__name__)

API_KEY = "fdfd01a4bf2748849f763d1efee731dd"

# -------------------------------------------------
# TÁVOLSÁG
# -------------------------------------------------
def distance_km(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) * 111


# -------------------------------------------------
# MÁRKA FELISMERÉS
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
    else:
        return "Benzinkút"


# -------------------------------------------------
# VALÓDI HÍRFIGYELŐ RADAR
# -------------------------------------------------
def get_real_radar():

    sources = [
        "https://www.portfolio.hu",
        "https://www.vg.hu",
        "https://www.economx.hu"
    ]

    keywords = [
        "üzemanyag",
        "benzin",
        "gázolaj",
        "drágul",
        "csökken",
        "változik"
    ]

    try:
        for url in sources:

            r = requests.get(url, timeout=10)
            text = r.text.lower()

            if any(word in text for word in keywords):

                # Ft keresés
                match = re.search(r'(\d+)\s*ft', text)

                if match:
                    price = match.group(1)
                    return f"⚠️ Friss hír: üzemanyagár változás várható ({price} Ft említve)"

                return "⚠️ Friss hír jelent meg üzemanyagár témában."

        return "✔️ Jelenleg nincs friss bejelentett árváltozás."

    except:
        return "⚠️ Radar átmenetileg nem elérhető."


# -------------------------------------------------
# KEZDŐOLDAL
# -------------------------------------------------
@app.route("/")
def home():
    return "Valós Radar API működik"


# -------------------------------------------------
# KUTAK + RADAR
# -------------------------------------------------
@app.route("/stations")
def stations():

    lat = request.args.get("lat", default=47.4979, type=float)
    lon = request.args.get("lon", default=19.0402, type=float)

    url = (
        f"https://api.geoapify.com/v2/places?"
        f"categories=service.vehicle.fuel"
        f"&filter=circle:{lon},{lat},5000"
        f"&limit=20"
        f"&apiKey={API_KEY}"
    )

    try:
        r = requests.get(url, timeout=20)
        data = r.json()

        stations = []

        for item in data["features"]:

            p = item["properties"]

            name = p.get("name", "Benzinkút")
            street = p.get("street", "")
            number = p.get("housenumber", "")

            full_name = name

            if street:
                full_name += ", " + street

            if number:
                full_name += " " + number

            item_lat = p["lat"]
            item_lon = p["lon"]

            dist = distance_km(lat, lon, item_lat, item_lon)

            stations.append({
                "name": full_name,
                "brand": detect_brand(name),
                "fuelType": "Ismeretlen",
                "price": 0,
                "lat": item_lat,
                "lon": item_lon,
                "distance": round(dist, 2)
            })

        stations.sort(key=lambda x: x["distance"])

        return jsonify({
            "radar": get_real_radar(),
            "stations": stations
        })

    except Exception as e:
        return jsonify({
            "radar": "⚠️ Nem elérhető a térképszerver.",
            "stations": []
        })


# -------------------------------------------------
if __name__ == "__main__":
    app.run()
