import os
import re
import math
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)
CORS(app)

# =====================================================
# CONFIG & RADAR (ÁRVÁLTOZÁS)
# =====================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_radar_data():
    """Beolvassa az árváltozásokat a holtankoljak.hu-ról"""
    try:
        url = "https://holtankoljak.hu/uzemanyag_arvaltozasok"
        r = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text().lower()
        
        r95 = re.search(r'benzin\s*(?:ára)?\s*([+-]?\s*\d+)\s*ft', text)
        rd = re.search(r'(?:gázolaj|diesel)\s*(?:ára)?\s*([+-]?\s*\d+)\s*ft', text)
        
        return (
            (r95.group(1).replace(" ", "") + " Ft") if r95 else "0 Ft",
            (rd.group(1).replace(" ", "") + " Ft") if rd else "0 Ft"
        )
    except:
        return "nincs adat", "nincs adat"

# =====================================================
# TÁVOLSÁG SZÁMÍTÁS (Haversine formula)
# =====================================================

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Föld sugara km-ben
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

# =====================================================
# VALÓS BENZINKUTAK LEKÉRÉSE GPS ALAPJÁN
# =====================================================

def get_nearby_fuel_stations(lat, lon):
    """
    Az Overpass API-t használjuk, ami az OpenStreetMap (OSM) valós, 
    hivatalos benzinkút adatbázisa. Ez tartalmazza az összes márkát (MOL, OMV, Shell, stb.)
    """
    try:
        # 15 km-es körzetben keresünk benzinkutakat a GPS pont körül
        query = f"""
        [out:json][timeout:15];
        node["amenity"="fuel"](around:15000, {lat}, {lon});
        out body;
        """
        url = "https://overpass-api.de/api/interpreter"
        response = requests.post(url, data=query, timeout=15)
        data = response.json()
        
        stations = []
        for element in data.get('elements', []):
            s_lat = element.get('lat')
            s_lon = element.get('lon')
            tags = element.get('tags', {})
            
            # Valós név és márka kinyerése
            name = tags.get('name', 'Benzinkút')
            brand = tags.get('brand', tags.get('operator', 'Független'))
            
            # Távolság kiszámítása a te GPS koordinátádtól
            dist = haversine(lat, lon, s_lat, s_lon)
            
            stations.append({
                "name": name,
                "brand": brand,
                "fuelType": "95 Benzin",
                "price": 612, # Az alap átlagár (ezt a frontend is tudja módosítani)
                "lat": s_lat,
                "lon": s_lon,
                "distance": dist
            })
            
        # Távolság szerinti rendezés (legközelebbi legfelül)
        stations.sort(key=lambda x: x["distance"])
        return stations
    except Exception as e:
        print(f"Hiba a GPS alapú keresésnél: {e}")
        return []

# =====================================================
# API ÚTVONALAK
# =====================================================

@app.route("/stations")
def stations():
    # A telefonod GPS-e küldi ezeket:
    try:
        user_lat = float(request.args.get("lat"))
        user_lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "Hiányzó vagy hibás GPS koordináták"}), 400

    # 1. Lekérjük a közeli VALÓS kutakat (OSM adatbázisból)
    nearby_stations = get_nearby_fuel_stations(user_lat, user_lon)
    
    # 2. Lekérjük az árváltozásokat (Radar)
    r95, rDiesel = get_radar_data()
    
    return jsonify({
        "status": "ok",
        "average95": 612,
        "averageDiesel": 635,
        "radarDay": "Péntektől" if datetime.today().weekday() < 4 else "Szerdától",
        "radar95": r95,
        "radarDiesel": rDiesel,
        "stations": nearby_stations
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
