import os
import re
import math
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

API_KEY = "fdfd01a4bf2748849f763d1efee731dd"

# -------------------------------------------------
# PONTOS TÁVOLSÁG (MÉTERBEN)
# -------------------------------------------------
def get_distance_result(lat1, lon1, lat2, lon2):
    R = 6371.0 # km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = R * c
    
    # Ha 1 km-nél kisebb, akkor méterben adjuk meg, ha nagyobb, marad km 2 tizedessel
    if distance_km < 1:
        return f"{int(distance_km * 1000)} m"
    else:
        return f"{round(distance_km, 2)} km"

# -------------------------------------------------
# RADAR ÉS ÁRAK (BENZIN ÉS DIESEL IS)
# -------------------------------------------------
def get_fuel_info():
    try:
        url = "https://holtankoljak.hu/uzemanyag_arvaltozasok"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, "html.parser")
        content = soup.get_text().lower()
        
        # Átlagárak keresése
        nums = re.findall(r'(\d{3})\s*ft', content)
        benzin_avg = int(nums[0]) if len(nums) >= 1 else 674
        diesel_avg = int(nums[1]) if len(nums) >= 2 else 705

        # Radar üzenet összeállítása (Benzin és Diesel külön)
        radar_parts = []
        
        # Keresés minták: "benzin ára 5 forinttal emelkedik" vagy "gázolaj ára 4 forinttal csökken"
        b_match = re.search(r'benzin.*?(\d+)\s*forint', content)
        d_match = re.search(r'(?:gázolaj|diesel).*?(\d+)\s*forint', content)
        
        type_word = "drágulás" if "emelkedik" in content or "nő" in content else "csökkenés"
        emoji = "⚠️" if "emelkedik" in content else "📉"

        if b_match and d_match:
            radar = f"{emoji} Várható {type_word}: B: +{b_match.group(1)} Ft | D: +{d_match.group(1)} Ft"
        elif b_match:
            radar = f"{emoji} Benzin {type_word} (+{b_match.group(1)} Ft)"
        else:
            radar = "✔️ Jelenleg nincs friss árváltozás"
            
        return benzin_avg, diesel_avg, radar
    except:
        return 674, 705, "⚠️ Árinfó nem elérhető"

def detect_brand(name):
    n = name.lower()
    if "shell" in n: return "Shell"
    if "mol" in n: return "MOL"
    if "omv" in n: return "OMV"
    if "lukoil" in n: return "Lukoil"
    if "avia" in n: return "Avia"
    if "auchan" in n: return "Auchan"
    if "orlen" in n: return "Orlen"
    return "Benzinkút"

def price_by_brand(base_price, brand):
    diff = {"Shell": 7, "OMV": 5, "MOL": 0, "Lukoil": -2, "Avia": -3, "Auchan": -7}
    return base_price + diff.get(brand, 0)

# -------------------------------------------------
# ROUTES
# -------------------------------------------------
@app.route("/stations")
def stations():
    lat = request.args.get("lat", default=47.6829, type=float)
    lon = request.args.get("lon", default=16.5988, type=float)

    avg_benzin, avg_diesel, radar = get_fuel_info()

    geo_url = (
        f"https://api.geoapify.com/v2/places?"
        f"categories=service.vehicle.fuel"
        f"&filter=circle:{lon},{lat},5000"
        f"&limit=30"
        f"&apiKey={API_KEY}"
    )

    try:
        r = requests.get(geo_url, timeout=15)
        data = r.json()
        stations_list = []

        for item in data.get("features", []):
            p = item["properties"]
            name = p.get("name", "Benzinkút")
            brand = detect_brand(name)
            address = p.get("address_line2", p.get("street", "Cím nem ismert"))
            
            alat, alon = p["lat"], p["lon"]
            
            # Formázott távolság (m vagy km)
            dist_str = get_distance_result(lat, lon, alat, alon)
            
            # Rendezéshez kell a nyers szám is (km)
            raw_dist = math.sqrt((lat-alat)**2 + (lon-alon)**2)

            price = price_by_brand(avg_benzin, brand)

            stations_list.append({
                "name": f"{brand} - {address}",
                "brand": brand,
                "fuelType": "95 Benzin",
                "price": price,
                "lat": alat,
                "lon": alon,
                "distance": dist_str, # Itt már szöveg megy ki (pl: "450 m")
                "raw_dist": raw_dist
            })

        stations_list.sort(key=lambda x: x["raw_dist"])

        return jsonify({
            "radar": radar,
            "average95": avg_benzin,
            "averageDiesel": avg_diesel,
            "stations": stations_list
        })

    except Exception as e:
        return jsonify({"error": str(e), "stations": []}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
