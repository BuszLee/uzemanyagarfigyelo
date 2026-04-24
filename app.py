from flask import Flask, jsonify, request
import requests
import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

app = Flask(__name__)

# -------------------------------------------------
# IDE írd a saját Geoapify kulcsodat
# -------------------------------------------------
API_KEY = "fdfd01a4bf2748849f763d1efee731dd"


# -------------------------------------------------
# TÁVOLSÁG
# -------------------------------------------------
def distance_km(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) * 111


# -------------------------------------------------
# MÁRKA
# -------------------------------------------------
def detect_brand(name):
    n = name.lower()

    if "shell" in n:
        return "Shell"
    elif "mol" in n:
        return "MOL"
    elif "omv" in n:
        return "OMV"
    elif "lukoil" in n:
        return "Lukoil"
    elif "avia" in n:
        return "Avia"
    else:
        return "Benzinkút"


# -------------------------------------------------
# DÁTUM PARSE
# -------------------------------------------------
def parse_date(txt):
    try:
        return datetime.strptime(
            txt[:25],
            "%a, %d %b %Y %H:%M:%S"
        )
    except:
        return None


# -------------------------------------------------
# FT KIOLVASÁS
# -------------------------------------------------
def extract_ft(text):

    patterns = [
        r'(\d+)\s*ft',
        r'(\d+)\s*forint'
    ]

    for p in patterns:
        m = re.search(p, text.lower())
        if m:
            return m.group(1)

    return None


# -------------------------------------------------
# SZÖVEG ELEMZÉS
# -------------------------------------------------
def analyze_text(title, desc):

    txt = (title + " " + desc).lower()

    keywords = [
        "üzemanyag",
        "benzin",
        "gázolaj",
        "tankol",
        "drágul",
        "csökken",
        "árváltozás",
        "holtankoljak"
    ]

    if not any(k in txt for k in keywords):
        return None

    amount = extract_ft(txt)

    if "drágul" in txt or "emelkedik" in txt:
        if amount:
            return f"⚠️ Várható drágulás (+{amount} Ft)"
        return "⚠️ Várható drágulás"

    if "csökken" in txt:
        if amount:
            return f"📉 Várható csökkenés (-{amount} Ft)"
        return "📉 Várható csökkenés"

    return "⚠️ Friss üzemanyagár hír jelent meg"


# -------------------------------------------------
# RSS FIGYELÉS
# -------------------------------------------------
def check_rss(url, source_name):

    try:
        r = requests.get(url, timeout=10)
        root = ET.fromstring(r.content)

        items = root.findall(".//item")

        for item in items[:5]:

            title = item.findtext("title", "")
            desc = item.findtext("description", "")
            pub = item.findtext("pubDate", "")

            result = analyze_text(title, desc)

            if result:
                return f"{result} | Forrás: {source_name}"

        return None

    except:
        return None


# -------------------------------------------------
# HTML FIGYELÉS (holtankoljak)
# -------------------------------------------------
def check_html(url, source_name):

    try:
        r = requests.get(url, timeout=10)
        text = r.text.lower()

        if any(x in text for x in [
            "benzin ára",
            "gázolaj ára",
            "üzemanyagár",
            "drágul",
            "csökken"
        ]):

            ft = extract_ft(text)

            if "drágul" in text:
                if ft:
                    return f"⚠️ Várható drágulás (+{ft} Ft) | Forrás: {source_name}"
                return f"⚠️ Várható drágulás | Forrás: {source_name}"

            if "csökken" in text:
                if ft:
                    return f"📉 Várható csökkenés (-{ft} Ft) | Forrás: {source_name}"
                return f"📉 Várható csökkenés | Forrás: {source_name}"

            return f"⚠️ Friss üzemanyagár hír | Forrás: {source_name}"

        return None

    except:
        return None


# -------------------------------------------------
# RADAR PRO
# -------------------------------------------------
def get_radar():

    sources = [

        # RSS-ek
        ("rss", "https://www.portfolio.hu/rss/all.xml", "Portfolio"),
        ("rss", "https://www.vg.hu/feed", "VG"),
        ("rss", "https://economx.hu/rss", "Economx"),

        # HTML
        ("html", "https://holtankoljak.hu", "Holtankoljak")
    ]

    for mode, url, name in sources:

        if mode == "rss":
            result = check_rss(url, name)
        else:
            result = check_html(url, name)

        if result:
            return result

    return "✔️ Jelenleg nincs friss bejelentett árváltozás."


# -------------------------------------------------
# KEZDŐOLDAL
# -------------------------------------------------
@app.route("/")
def home():
    return "Radar Pro API működik"


# -------------------------------------------------
# KUTAK + RADAR
# -------------------------------------------------
@app.route("/stations")
def stations():

    lat = request.args.get("lat", default=47.4979, type=float)
    lon = request.args.get("lon", default=19.0402, type=float)

    url = (
        f"https://api.geoapify.com/v2/places?"
        f"categories=service.vehicle.fuel"
        f"&filter=circle:{lon},{lat},5000"
        f"&limit=25"
        f"&apiKey={API_KEY}"
    )

    try:
        r = requests.get(url, timeout=20)
        data = r.json()

        result = []

        for item in data["features"]:

            p = item["properties"]

            name = p.get("name", "Benzinkút")
            street = p.get("street", "")
            number = p.get("housenumber", "")

            full_name = name

            if street:
                full_name += ", " + street

            if number:
                full_name += " " + number

            alat = p["lat"]
            alon = p["lon"]

            dist = distance_km(lat, lon, alat, alon)

            result.append({
                "name": full_name,
                "brand": detect_brand(name),
                "fuelType": "Ismeretlen",
                "price": 0,
                "lat": alat,
                "lon": alon,
                "distance": round(dist, 2)
            })

        result.sort(key=lambda x: x["distance"])

        return jsonify({
            "radar": get_radar(),
            "stations": result
        })

    except Exception as e:
        return jsonify({
            "radar": "⚠️ Térképszerver nem elérhető.",
            "stations": []
        })


# -------------------------------------------------
if __name__ == "__main__":
    app.run()
