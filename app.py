from flask import Flask, jsonify, request
import random

app = Flask(__name__)

@app.route("/")
def home():
    return "Fuel API running"

@app.route("/stations")
def stations():

    lat = request.args.get("lat", 47.4979, type=float)
    lon = request.args.get("lon", 19.0402, type=float)

    stations = [
        {
            "name": "OMV Budapest, Váci út",
            "lat": lat + 0.010,
            "lon": lon + 0.005,
            "fuelType": "95",
            "price": 617
        },
        {
            "name": "Shell Budapest, Hungária körút",
            "lat": lat - 0.008,
            "lon": lon + 0.012,
            "fuelType": "95",
            "price": 621
        },
        {
            "name": "MOL Budapest, Üllői út",
            "lat": lat + 0.006,
            "lon": lon - 0.010,
            "fuelType": "95",
            "price": 612
        },
        {
            "name": "Auchan Benzinkút",
            "lat": lat - 0.012,
            "lon": lon - 0.008,
            "fuelType": "95",
            "price": 606
        },
        {
            "name": "AVIA Budapest",
            "lat": lat + 0.015,
            "lon": lon + 0.002,
            "fuelType": "95",
            "price": 609
        }
    ]

    return jsonify({
        "stations": stations
    })

if __name__ == "__main__":
    app.run()
