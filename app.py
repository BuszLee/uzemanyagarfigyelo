import os
import re
import math
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from bs4 import BeautifulSoup

app = Flask(__name__)
# A CORS(app) kritikus: ez engedi, hogy a telefonos appod elérje a szervert
CORS(app, resources={r"/*": {"origins": "*"}})

API_KEY = "fdfd01a4bf2748849f763d1efee731dd"

def get_distance_result(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    dist_km = R * c
    return f"{int(dist_km * 1000)} m" if dist_km < 1 else f"{round(dist_km, 2)} km"

def get_fuel_info():
    try:
        url = "https://holtankoljak.hu/uzemanyag_arvaltozasok"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = 'utf-8'
        content = r.text.lower()
        
        nums = re.findall(r'(\d{3})\s*ft', content)
        b_avg = int(nums[0]) if len(nums) >= 1 else 674
        d_avg = int(nums[1]) if len(nums) >= 2 else 705

        b_match = re.search(r'benzin.*?(\d+)\s*forint', content)
        d_match = re.search(r'(?:gázolaj|diesel).*?(\d+)\s*forint', content)
        
        type_w = "drágulás" if "emelkedik" in content or "nő" in content else "csökkenés"
        emoji = "⚠️" if "emelkedik" in content else "📉"

        if b_match and d_match:
            radar = f"{emoji} Várható {type_w}: B: +{b_match.group(1)} Ft | D: +{d_match.group(1)} Ft"
        elif b_match:
            radar = f"{emoji} Benzin {type_w} (+{b_match.group(1)} Ft)"
        else:
            radar = "✔️ Jelenleg nincs friss árváltozás"
            
        return b_avg, d_avg, radar
    except:
        return 674, 705, "⚠️ Árinfó nem elérhető"

@app.route("/")
def home():
    return jsonify({"status": "ok", "message": "API is running. Use /stations"}), 200

@app.route("/stations")
def stations():
    # Kinyerjük a koordinátákat. Ha nincsenek, Sopront használjuk alapnak.
    try:
        lat = float(request.args.get("lat", 47.6829))
        lon = float(request.args.get("lon", 16.5988))
    except:
        lat, lon = 47.6829, 16.5988

    avg_95, avg_d, radar = get_fuel_info()

    geo_url = f"https://api.geoapify.com/v2/places?categories=service.vehicle.fuel&filter=circle:{lon},{lat},5000&limit=30&apiKey={API_KEY}"

    try:
        r = requests.get(geo_url, timeout=15)
        data = r.json()
        res = []

        for item in data.get("features", []):
            p = item["properties"]
            brand = p.get("brand", p.get("name", "Benzinkút")).split()[0]
            if brand.lower() not in ["mol", "omv", "shell", "lukoil", "avia", "auchan", "orlen"]:
                brand = "Benzinkút"
            
            addr = p.get("address_line2", "Ismeretlen cím")
            alat, alon = p["lat"], p["lon"]
            dist_str = get_distance_result(lat, lon, alat, alon)
            
            # Nyers távolság a rendezéshez
            raw_d = math.sqrt((lat-alat)**2 + (lon-alon)**2)

            res.append({
                "name": f"{brand} - {addr}",
                "brand": brand,
                "fuelType": "95 Benzin",
                "price": avg_95 + (8 if brand == "Shell" else 5 if brand == "OMV" else 0),
                "lat": alat, "lon": alon,
                "distance": dist_str,
                "raw_dist": raw_d
            })

        res.sort(key=lambda x: x["raw_dist"])
        return jsonify({
            "radar": radar,
            "average95": avg_95,
            "averageDiesel": avg_d,
            "stations": res
        })
    except Exception as e:
        return jsonify({"error": str(e), "stations": []}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
