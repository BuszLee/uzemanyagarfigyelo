import os
import re
import math
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# -------------------------------------------------
# SAJÁT GEOAPIFY KULCSOD
# -------------------------------------------------
API_KEY = "fdfd01a4bf2748849f763d1efee731dd"

# -------------------------------------------------
# TÁVOLSÁG (Pontosabb Haversine formula)
# -------------------------------------------------
def distance_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

# -------------------------------------------------
# MÁRKA FELISMERÉS
# -------------------------------------------------
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

# -------------------------------------------------
# HOLTANKOLJAK ADATOK (Árak és Radar)
# -------------------------------------------------
def get_fuel_info():
    try:
        url = "https://holtankoljak.hu/uzemanyag_arvaltozasok"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = 'utf-8'
        text = r.text.lower()
        
        # Árak kinyerése
        nums = re.findall(r'(\d{3})\s*ft', text)
        benzin = int(nums[0]) if len(nums) >= 1 else 612
        diesel = int(nums[1]) if len(nums) >= 2 else 635

        # Radar üzenet
        radar = "✔️ Jelenleg nincs friss árváltozás"
        if "emelkedik" in text:
            m = re.search(r'(\d+)\s*forint', text)
            radar = f"⚠️ Várható drágulás (+{m.group(1)} Ft)" if m else "⚠️ Várható drágulás"
        elif "csökken" in text:
            m = re.search(r'(\d+)\s*forint', text)
            radar = f"📉 Várható csökkenés (-{m.group(1)} Ft)" if m else "📉 Várható csökkenés"
            
        return benzin, diesel, radar
    except:
        return 612, 635, "⚠️ Árinfó nem elérhető"

def price_by_brand(base_price, brand):
    diff = {"Shell": 7, "OMV": 5, "MOL": 0, "Lukoil": -2, "Avia": -3, "Auchan": -7}
    return base_price + diff.get(brand, 0)

# -------------------------------------------------
# ROUTES
# -------------------------------------------------
@app.route("/")
def home():
    return "Benzinkút Figyelő API Online"

@app.route("/stations")
def stations():
    # Koordináták fogadása (Sopron az alapértelmezett, ha nincs megadva)
    lat = request.args.get("lat", default=47.6829, type=float)
    lon = request.args.get("lon", default=16.5988, type=float)

    avg_benzin, avg_diesel, radar = get_fuel_info()

    # Geoapify API hívás (5km-es körzet)
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
            
            # Cím összeállítása
            address = p.get("address_line2", p.get("street", "Cím nem ismert"))
            
            alat, alon = p["lat"], p["lon"]
            dist = distance_km(lat, lon, alat, alon)
            
            price = price_by_brand(avg_benzin, brand)

            stations_list.append({
                "name": f"{brand} - {address}",
                "brand": brand,
                "fuelType": "95 Benzin",
                "price": price,
                "lat": alat,
                "lon": alon,
                "distance": dist
            })

        # Rendezés távolság szerint
        stations_list.sort(key=lambda x: x["distance"])

        return jsonify({
            "radar": radar,
            "average95": avg_benzin,
            "averageDiesel": avg_diesel,
            "stations": stations_list
        })

    except Exception as e:
        return jsonify({"error": str(e), "stations": []}), 500

if __name__ == "__main__":
    # Render-kompatibilis indítás
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
