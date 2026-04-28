import os
import re
import math
import time
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)
# Fontos: A frontended (pl. GitHub Pages) csak akkor éri el a backendet, ha a CORS be van állítva
CORS(app)

# =====================================================
# CONFIG & HEADERS
# =====================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7"
}

# =====================================================
# SEGÉDFÜGGVÉNYEK
# =====================================================

def get_radar_data():
    """Beolvassa az árváltozásokat a holtankoljak.hu-ról"""
    try:
        url = "https://holtankoljak.hu/uzemanyag_arvaltozasok"
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, "html.parser")
        
        # A teljes szöveges tartalmat nézzük
        text = soup.get_text().lower()
        
        # Alapértelmezett értékek
        radar_95 = "+0 Ft"
        radar_diesel = "+0 Ft"
        
        # Reguláris kifejezések az árak kinyeréséhez
        # Keresünk olyat, hogy "benzin" majd utána egy számot és a "ft" szót
        m1 = re.search(r'benzin\s*(?:ára|esetében)?\s*([+-]?\s*\d+)\s*ft', text)
        if m1:
            radar_95 = f"{m1.group(1).replace(' ', '')} Ft"
            
        m2 = re.search(r'(?:gázolaj|diesel)\s*(?:ára|esetében)?\s*([+-]?\s*\d+)\s*ft', text)
        if m2:
            radar_diesel = f"{m2.group(1).replace(' ', '')} Ft"
            
        return radar_95, radar_diesel
    except Exception as e:
        print(f"Radar hiba: {e}")
        return "+? Ft", "+? Ft"

def get_next_change_day():
    wd = datetime.today().weekday()
    if wd in [0, 1]: return "Szerdától"
    if wd in [2, 3]: return "Péntektől"
    return "Jövő héten"

# =====================================================
# ÚTVONALAK (ROUTES)
# =====================================================

@app.route("/")
def home():
    return jsonify({
        "message": "Benzinkút API Online",
        "status": "ready",
        "usage": "/stations?lat=47.49&lon=19.04"
    })

@app.route("/stations")
def stations():
    # Koordináták kinyerése a kérésből
    try:
        user_lat = float(request.args.get("lat", 47.4979))
        user_lon = float(request.args.get("lon", 19.0402))
    except ValueError:
        return jsonify({"error": "Érvénytelen koordináták"}), 400

    # Árváltozások lekérése
    r95, rDiesel = get_radar_data()
    
    # Megjegyzés: A konkrét kutak listáját érdemesebb a frontendnek 
    # közvetlenül az Overpass API-tól kérnie, hogy elkerüld a geocoding lassúságát.
    # Ez a rész most egy példa statikus adatot ad vissza a struktúra miatt.
    
    return jsonify({
        "status": "ok",
        "radarDay": get_next_change_day(),
        "radar95": r95,
        "radarDiesel": rDiesel,
        "average95": 612, # Statikus vagy számított átlag
        "averageDiesel": 635,
        "stations": [] # Itt küldheted tovább a feldolgozott kutakat
    })

# =====================================================
# INDÍTÁS
# =====================================================

if __name__ == "__main__":
    # Render környezetben a PORT-ot a környezeti változóból kell venni
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
