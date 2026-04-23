from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return "Fuel API running"

@app.route("/stations")
def stations():

    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)

    if lat is None or lon is None:
        lat = 47.4979
        lon = 19.0402

    query = f"""
    [out:json];
    (
      node["amenity"="fuel"](around:5000,{lat},{lon});
      way["amenity"="fuel"](around:5000,{lat},{lon});
      relation["amenity"="fuel"](around:5000,{lat},{lon});
    );
    out center;
    """

    url = "https://overpass-api.de/api/interpreter"

    r = requests.get(url, params={"data": query}, timeout=20)
    data = r.json()

    stations = []

    for item in data["elements"]:

        tags = item.get("tags", {})

        name = tags.get("name", "Benzinkút")

        if "lat" in item:
            station_lat = item["lat"]
            station_lon = item["lon"]
        else:
            station_lat = item["center"]["lat"]
            station_lon = item["center"]["lon"]

        stations.append({
            "name": name,
            "lat": station_lat,
            "lon": station_lon,
            "fuelType": "95",
            "price": 615
        })

    return jsonify({
        "stations": stations
    })

if __name__ == "__main__":
    app.run()
