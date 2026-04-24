from flask import Flask, jsonify, request
import requests
import math

app = Flask(__name__)

API_KEY = "fdfd01a4bf2748849f763d1efee731dd"

# -----------------------------------------
# Távolság km
# -----------------------------------------
def distance_km(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1-lat2)**2 + (lon1-lon2)**2) * 111

# -----------------------------------------
# Márka felismerés
# -----------------------------------------
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

# -----------------------------------------
# Főoldal
# -----------------------------------------
@app.route("/")
def home():
    return "Geoapify API működik"

# -----------------------------------------
# Kutak
# -----------------------------------------
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

            props = item["properties"]

            name = props.get("name", "Benzinkút")
            street = props.get("street", "")
            housenumber = props.get("housenumber", "")
            city = props.get("city", "")

            full_name = name

            if street:
                full_name += ", " + street

            if housenumber:
                full_name += " " + housenumber

            if city:
                full_name += ", " + city

            item_lat = props["lat"]
            item_lon = props["lon"]

            dist = distance_km(lat, lon, item_lat, item_lon)

            brand = detect_brand(name)

            stations.append({
                "name": full_name,
                "brand": brand,
                "fuelType": "95 Benzin",
                "price": 0,
                "lat": item_lat,
                "lon": item_lon,
                "distance": dist
            })

        stations.sort(key=lambda x: x["distance"])

        return jsonify({
            "stations": stations
        })

    except Exception as e:
        return jsonify({
            "error": str(e),
            "stations": []
        })

if __name__ == "__main__":
    app.run()
