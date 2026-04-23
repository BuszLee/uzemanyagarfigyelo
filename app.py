from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return "Fuel API running"

@app.route("/stations")
def stations():

    lat = request.args.get("lat", 47.4979, type=float)
    lon = request.args.get("lon", 19.0402, type=float)

    try:
        query = f"""
        [out:json];
        (
          node["amenity"="fuel"](around:5000,{lat},{lon});
          way["amenity"="fuel"](around:5000,{lat},{lon});
        );
        out center;
        """

        r = requests.get(
            "https://overpass-api.de/api/interpreter",
            params={"data": query},
            timeout=15
        )

        data = r.json()

        stations = []

        for item in data["elements"]:

            tags = item.get("tags", {})
            name = tags.get("name", "Benzinkút")

            if "lat" in item:
                slat = item["lat"]
                slon = item["lon"]
            else:
                slat = item["center"]["lat"]
                slon = item["center"]["lon"]

            stations.append({
                "name": name,
                "lat": slat,
                "lon": slon,
                "fuelType": "95",
                "price": 615
            })

        if len(stations) > 0:
            return jsonify({"stations": stations})

    except:
        pass

    # tartalék rendszer
    fallback = [
        {
            "name": "OMV közeli kút",
            "lat": lat + 0.01,
            "lon": lon + 0.01,
            "fuelType": "95",
            "price": 617
        },
        {
            "name": "MOL közeli kút",
            "lat": lat - 0.01,
            "lon": lon,
            "fuelType": "95",
            "price": 612
        },
        {
            "name": "Shell közeli kút",
            "lat": lat,
            "lon": lon - 0.01,
            "fuelType": "95",
            "price": 621
        }
    ]

    return jsonify({"stations": fallback})

if __name__ == "__main__":
    app.run()
