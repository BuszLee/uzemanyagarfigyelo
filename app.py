from flask import Flask, jsonify, request
import math

app = Flask(__name__)

# ---------------------------------------------------
# MINTA KUTAK (Magyarország)
# ---------------------------------------------------
stations_db = [
    {"name": "MOL Budapest, Váci út", "brand": "MOL", "lat": 47.5310, "lon": 19.0670},
    {"name": "Shell Budapest, Árpád híd", "brand": "Shell", "lat": 47.5325, "lon": 19.0450},
    {"name": "OMV Budapest, Hungária körút", "brand": "OMV", "lat": 47.5050, "lon": 19.0950},
    {"name": "MOL Budapest, Üllői út", "brand": "MOL", "lat": 47.4550, "lon": 19.1400},
    {"name": "Shell Budapest, Budaörsi út", "brand": "Shell", "lat": 47.4700, "lon": 19.0200},
    {"name": "OMV Budapest, Szentendrei út", "brand": "OMV", "lat": 47.5600, "lon": 19.0500},
]

# ---------------------------------------------------
# TÁVOLSÁG
# ---------------------------------------------------
def calc_distance(lat1, lon1, lat2, lon2):
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
# ÁRAK
# ---------------------------------------------------
def get_price(brand):
    prices = {
        "MOL": 622,
        "Shell": 639,
        "OMV": 631
    }
    return prices.get(brand, 625)


# ---------------------------------------------------
# FŐ OLDAL
# ---------------------------------------------------
@app.route("/")
def home():
    return "Server működik"


# ---------------------------------------------------
# API
# ---------------------------------------------------
@app.route("/stations")
def stations():

    lat = float(request.args.get("lat", 47.4979))
    lon = float(request.args.get("lon", 19.0402))

    result = []

    for s in stations_db:

        dist = calc_distance(lat, lon, s["lat"], s["lon"])

        result.append({
            "name": s["name"],
            "brand": s["brand"],
            "fuelType": "95 Benzin",
            "price": get_price(s["brand"]),
            "lat": s["lat"],
            "lon": s["lon"],
            "distance": dist
        })

    result.sort(key=lambda x: x["distance"])

    return jsonify({"stations": result[:20]})


if __name__ == "__main__":
    app.run()
