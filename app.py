from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status": "online"}

@app.get("/stations")
def stations():
    return {
        "stations": [
            {
                "name": "MOL Ipar körút",
                "brand": "MOL",
                "lat": 47.67,
                "lon": 16.61,
                "price": 619
            },
            {
                "name": "Shell Lackner út",
                "brand": "Shell",
                "lat": 47.69,
                "lon": 16.58,
                "price": 632
            }
        ]
    }
