import os
import re
import math
import requests
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from bs4 import BeautifulSoup

app = Flask(__name__)
# A lehető legengedékenyebb CORS beállítás
CORS(app, resources={r"/*": {"origins": "*"}})

API_KEY = "fdfd01a4bf2748849f763d1efee731dd"

# --- Távolság kalkulátor maradt a régi, bevált ---
def get_distance_result(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = R * c
    return f"{int(distance_km * 1000)} m" if distance_km < 1 else f"{round(distance_km, 2)} km"

def get_fuel_info():
    try:
        url = "https://holtankoljak.hu/uzemanyag_arvaltozasok"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = 'utf-8'
        content = r.text.lower()
        nums = re.findall(r'(\d{3})\s*ft', content)
        b_avg = int(nums[0]) if len(nums) >= 1 else 674
        d_avg = int(nums[1]) if len(nums) >= 2 else 705
        
        b_valtozas = re.search(r'benzin.*?(\d+)\s*forint', content)
        d_valtozas = re.search(r'(?:gázolaj|diesel).*?(\d+)\s*forint', content)
        
        type_w = "drágulás" if "emelkedik" in content or "nő" in content else "csökkenés"
        emoji = "⚠️" if "emelkedik" in content else "📉"
        
        if b_valtozas and d_valtozas:
            radar = f"{emoji} Várható {type_w}: B: +{b_valtozas.group(1)} Ft | D: +{d_valtozas.group(1)} Ft"
        elif b_valtozas:
            radar = f"{emoji} Benzin {type_w} (+{b_valtozas.group(1)} Ft)"
        else:
            radar = "✔️ Nincs friss árváltozás"
        return b_avg, d_avg, radar
    except:
        return 674, 705, "⚠️ Árinfó nem elérhető"

@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Origin-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Origin-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

@app.route("/")
def home():
    return "API ONLINE"

@app.route("/stations")
def stations():
    lat = request.args.get("lat", default=47.6829, type=float)
    lon = request.args.get("lon", default=16.5988, type=float)
    b_avg, d_avg, radar = get_fuel_info()

    geo_url = f"https://api.geoapify.com/v2/places?categories=service.vehicle.fuel&filter=circle:{lon},{lat},5000&limit=30&apiKey={API_KEY}"

    try:
        r = requests.get(geo_url, timeout=15)
        data = r.json()
        output = []
        for item in data.get("features", []):
            p = item["properties"]
            name = p.get("name", "Benzinkút")
            brand = "MOL" if "mol" in name.lower() else "OMV" if "omv" in name.lower() else "SHELL" if "shell" in name.lower() else "Benzinkút"
            addr = p.get("address_line2", "Ismeretlen cím")
            alat, alon = p["lat"], p["lon"]
            
            # Ez a rész felel a rendezésért
            raw_dist = math.sqrt((lat-alat)**2 + (lon-alon)**2)

            output.append({
                "name": f"{brand} - {addr}",
                "brand": brand,
                "fuelType": "95 Benzin",
                "price": b_avg + (5 if brand == "OMV" else 7 if brand == "SHELL" else 0),
                "lat": alat,
                "lon": alon,
                "distance": get_distance_result(lat, lon, alat, alon),
                "raw_dist": raw_dist
            })
        
        output.sort(key=lambda x: x["raw_dist"])
        
        return jsonify({
            "radar": radar,
            "average95": b_avg,
            "averageDiesel": d_avg,
            "stations": output
        })
    except Exception as e:
        return jsonify({"error": str(e), "stations": []})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
