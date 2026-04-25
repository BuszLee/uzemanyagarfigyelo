from flask import Flask, jsonify, request
import requests
import math
import re

app = Flask(__name__)

# -------------------------------------------------
# SAJÁT GEOAPIFY KULCS
# -------------------------------------------------
API_KEY = "fdfd01a4bf2748849f763d1efee731dd"


# -------------------------------------------------
# TÁVOLSÁG
# -------------------------------------------------
def distance_km(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) * 111


# -------------------------------------------------
# MÁRKA FELISMERÉS
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
    elif "auchan" in n:
        return "Auchan"
    else:
        return "Benzinkút"


# -------------------------------------------------
# HOLTANKOLJAK ÁTLAGÁRAK
# -------------------------------------------------
def get_average_prices():

    try:
        url = "https://holtankoljak.hu/uzemanyag_arvaltozasok"

        r = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        text = r.text.lower()

        nums = re.findall(r'(\d{3})\s*ft', text)

        if len(nums) >= 2:
            benzin = int(nums[0])
            diesel = int(nums[1])

            return benzin, diesel

        return 620, 640

    except:
        return 620, 640


# -------------------------------------------------
# VÁLTOZÁS INFO
# -------------------------------------------------
def get_change_info():

    try:
        url = "https://holtankoljak.hu/uzemanyag_arvaltozasok"

        r = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        text = r.text.lower()

        if "emelkedik" in text:
            m = re.search(r'(\d+)\s*forint', text)

            if m:
                return f"⚠️ Várható drágulás (+{m.group(1)} Ft)"

            return "⚠️ Várható drágulás"

        if "csökken" in text:
            m = re.search(r'(\d+)\s*forint', text)

            if m:
                return f"📉 Várható csökkenés (-{m.group(1)} Ft)"

            return "📉 Várható csökkenés"

        return "✔️ Jelenleg nincs friss árváltozás"

    except:
        return "⚠️ Árfigyelő átmenetileg nem elérhető"


# -------------------------------------------------
# MÁRKA ÁR KORREKCIÓ
# -------------------------------------------------
def price_by_brand(base_price, brand):

    diff = {
        "Shell": 8,
        "OMV": 5,
        "MOL": 0,
        "Lukoil": -2,
        "Avia": -3,
        "Auchan": -6,
        "Benzinkút": 0
    }

    return base_price + diff.get(brand, 0)


# -------------------------------------------------
# HOME
# -------------------------------------------------
@app.route("/")
def home():
    return "Holtankoljak PRO API működik"


# -------------------------------------------------
# STATIONS
# -------------------------------------------------
@app.route("/stations")
def stations():

    lat = request.args.get("lat", default=47.4979, type=float)
    lon = request.args.get("lon", default=19.0402, type=float)

    avg_benzin, avg_diesel = get_average_prices()
    radar = get_change_info()

    geo_url = (
        f"https://api.geoapify.com/v2/places?"
        f"categories=service.vehicle.fuel"
        f"&filter=circle:{lon},{lat},5000"
        f"&limit=25"
        f"&apiKey={API_KEY}"
    )

    try:
        r = requests.get(geo_url, timeout=20)
        data = r.json()

        stations = []

        for item in data["features"]:

            p = item["properties"]

            name = p.get("name", "Benzinkút")
            street = p.get("street", "")
            number = p.get("housenumber", "")

            full = name

            if street:
                full += ", " + street

            if number:
                full += " " + number

            alat = p["lat"]
            alon = p["lon"]

            dist = distance_km(lat, lon, alat, alon)

            brand = detect_brand(name)

            price = price_by_brand(avg_benzin, brand)

            stations.append({
                "name": full,
                "brand": brand,
                "fuelType": "95 Benzin",
                "price": price,
                "lat": alat,
                "lon": alon,
                "distance": round(dist, 2)
            })

        stations.sort(key=lambda x: x["distance"])

        return jsonify({
            "radar": radar,
            "average95": avg_benzin,
            "averageDiesel": avg_diesel,
            "stations": stations
        })

    except Exception as e:

        return jsonify({
            "radar": "⚠️ Térképszerver nem elérhető",
            "stations": []
        })


# -------------------------------------------------
if __name__ == "__main__":
    app.run()
