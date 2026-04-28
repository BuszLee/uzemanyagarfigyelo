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

# A te kulcsod az IP alapú helymeghatározáshoz
IP_GEOLOCATION_KEY = "fdfd01a4bf2748849f763d1efee731dd"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# =====================================================
# SEGÉDFÜGGVÉNYEK
# =====================================================

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

def get_radar_data():
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

def get_coords_by_ip():
    """Ha nincs GPS, az API kulccsal lekérjük a koordinátákat IP alapján"""
    try:
        url = f"https://ipgeolocation.abstractapi.com/v1/?api_key={IP_GEOLOCATION_KEY}"
        r = requests.get(url, timeout=5)
        data = r.json()
        return float(data['latitude']), float(data['longitude'])
    except:
        return 47.4979, 19.0402  # Budapest fallback

# =====================================================
# ÚTVONALAK
# =====================================================

@app.route("/stations")
def stations():
    # 1. Koordináták megszerzése (URL-ből vagy IP-ből a kulcsoddal)
    lat_param = request.args.get("lat")
    lon_param = request.args.get("lon")

    if lat_param and lon_param:
        try:
            user_lat = float(lat_param)
            user_lon = float(lon_param)
        except:
            user_lat, user_lon = get_coords_by_ip()
    else:
        # Ha a böngészőben csak simán megnyitod, a kulcsodat használja!
        user_lat, user_lon = get_coords_by_ip()

    # 2. Közeli valós kutak keresése (Overpass API)
    nearby_stations = []
    try:
        query = f"""
        [out:json][timeout:15];
        node["amenity"="fuel"](around:15000, {user_lat}, {user_lon});
        out body;
        """
        r = requests.post("https://overpass-api.de/api/interpreter", data=query, timeout=15)
        data = r.json()
        
        for el in data.get('elements', []):
            tags = el.get('tags', {})
            dist = haversine(user_lat, user_lon, el['lat'], el['lon'])
            nearby_stations.append({
                "name": tags.get('name', 'Benzinkút'),
                "brand": tags.get('brand', tags.get('operator', 'Független')),
                "fuelType": "95 Benzin",
                "price": 612,
                "lat": el['lat'],
                "lon": el['lon'],
                "distance": dist
            })
        nearby_stations.sort(key=lambda x: x["distance"])
    except:
        pass

    # 3. Radar adatok
    r95, rDiesel = get_radar_data()

    return jsonify({
        "status": "ok",
        "location_source": "GPS" if lat_param else "IP-API",
        "user_lat": user_lat,
        "user_lon": user_lon,
        "radar95": r95,
        "radarDiesel": rDiesel,
        "stations": nearby_stations[:20]
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
