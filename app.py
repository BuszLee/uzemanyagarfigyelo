from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# napi frissíthető árlista
prices = {
    "Shell": 611,
    "OMV": 608,
    "MOL": 603,
    "ALDI": 599,
    "FullEnergy": 596,
    "Benzinkút": 605
}

@app.route("/")
def home():
    return jsonify({"status": "ok"})

@app.route("/stations")
def stations():
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    query = f"""
    [out:json];
    (
      node["amenity"="fuel"](around:8000,{lat},{lon});
      way["amenity"="fuel"](around:8000,{lat},{lon});
      relation["amenity"="fuel"](around:8000,{lat},{lon});
    );
    out center;
    """

    url = "https://overpass-api.de/api/interpreter"
    r = requests.get(url, params={"data": query})
    data = r.json()

    stations = []

    for item in data["elements"]:
        tags = item.get("tags", {})
        name = tags.get("name", "Benzinkút")

        brand = "Benzinkút"

        for b in ["Shell", "OMV", "MOL", "ALDI", "FullEnergy"]:
            if b.lower() in name.lower():
                brand = b

        price = prices.get(brand, 605)

        lat2 = item.get("lat", item.get("center", {}).get("lat"))
        lon2 = item.get("lon", item.get("center", {}).get("lon"))

        stations.append({
            "name": name,
            "brand": brand,
            "fuelType": "95",
            "price": price,
            "lat": lat2,
            "lon": lon2
        })

    return jsonify({"stations": stations})
