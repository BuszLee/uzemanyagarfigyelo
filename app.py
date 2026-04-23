from flask import Flask, jsonify, request
import requests
import math

app = Flask(__name__)

# ---------------------------------------------------
# TÁVOLSÁG (km)
# ---------------------------------------------------
def distance_km(lat1, lon1, lat2, lon2):
    r = 6371

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
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
    elif "lukoil" in n:
        return "Lukoil"
    elif "orlen" in n:
        return "Orlen"
    elif "avia" in n:
        return "Avia"
    else:
        return "Benzinkút"


# ---------------------------------------------------
# CÍM ÖSSZERAKÁS
# ---------------------------------------------------
def build_address(tags):
    street = tags.get("addr:street", "")
    house = tags.get("addr:housenumber", "")
    city = tags.get("addr:city", "")

    line1 = f"{street} {house}".strip()
    line2 = city.strip()

    if line1 and line2:
        return f"{line1}, {line2}"
    elif line1:
        return line1
    elif line2:
        return line2
    else:
        return "Cím nem elérhető"


# ---------------------------------------------------
# FŐOLDAL
# ---------------------------------------------------
@app.route("/")
def home():
    return "Valódi kutas szerver működik"


# ---------------------------------------------------
# API
# ---------------------------------------------------
@app.route("/stations")
def stations():

    try:
        lat = float(request.args.get("lat", 47.4979))
        lon = float(request.args.get("lon", 19.0402))

        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"="fuel"](around:10000,{lat},{lon});
          way["amenity"="fuel"](around:10000,{lat},{lon});
          relation["amenity"="fuel"](around:10000,{lat},{lon});
        );
        out center tags;
        """

        r = requests.get(
            "https://overpass-api.de/api/interpreter",
            params={"data": query},
            timeout=30
        )

        data = r.json()

        result = []

        for item in data["elements"]:

            tags = item.get("tags", {})

            name = tags.get("name", "Benzinkút")
            brand = detect_brand(name)
            address = build_address(tags)

            if "lat" in item:
                s_lat = item["lat"]
                s_lon = item["lon"]
            else:
                center = item.get("center", {})
                s_lat = center.get("lat")
                s_lon = center.get("lon")

            if s_lat is None or s_lon is None:
                continue

            dist = distance_km(lat, lon, s_lat, s_lon)

            result.append({
                "name": name,
                "brand": brand,
                "fuelType": address,
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
    app.run()
