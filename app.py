from flask import Flask, jsonify, request
import requests
import math

app = Flask(__name__)

# ---------------------------------------------------
# TÁVOLSÁG KM
# ---------------------------------------------------
def distance_km(lat1, lon1, lat2, lon2):
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
    return r * c


# ---------------------------------------------------
# MÁRKA FELISMERÉS
# ---------------------------------------------------
def detect_brand(name):
    n = name.lower()

    if "shell" in n:
        return "Shell"
    elif "mol" in n:
        return "MOL"
    elif "omv" in n:
        return "OMV"
    elif "orlen" in n:
        return "Orlen"
    elif "lukoil" in n:
        return "Lukoil"
    else:
        return "Benzinkút"


# ---------------------------------------------------
# FŐOLDAL
# ---------------------------------------------------
@app.route("/")
def home():
    return "GPS közeli kutas szerver működik"


# ---------------------------------------------------
# API
# ---------------------------------------------------
@app.route("/stations")
def stations():

    try:
        lat = float(request.args.get("lat", 47.4979))
        lon = float(request.args.get("lon", 19.0402))

        # OpenStreetMap Nominatim keresés
        url = "https://nominatim.openstreetmap.org/search"

        params = {
            "q": "fuel station",
            "format": "jsonv2",
            "limit": 50,
            "bounded": 1,
            "viewbox": f"{lon-0.15},{lat+0.15},{lon+0.15},{lat-0.15}",
            "countrycodes": "hu"
        }

        headers = {
            "User-Agent": "uzemanyagarfigyelo"
        }

        r = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=20
        )

        data = r.json()

        result = []

        for item in data:

            name = item.get("display_name", "Benzinkút")
            s_lat = float(item["lat"])
            s_lon = float(item["lon"])

            dist = distance_km(lat, lon, s_lat, s_lon)

            brand = detect_brand(name)

            result.append({
                "name": name.split(",")[0],
                "brand": brand,
                "fuelType": name,
                "price": 0,
                "lat": s_lat,
                "lon": s_lon,
                "distance": dist
            })

        result.sort(key=lambda x: x["distance"])

        return jsonify({
            "stations": result[:25]
        })

    except Exception as e:

        return jsonify({
            "stations": [],
            "error": str(e)
        })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
