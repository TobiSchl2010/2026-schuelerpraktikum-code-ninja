import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os 

load_dotenv()

MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_PORT = os.getenv("MONGO_PORT")
MONGO_DB = os.getenv("MONGO_DB")

client = AsyncIOMotorClient(
    f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
)
db = client["data"]
collection = db["data"]

komponenten = [
    "thruster_1.a",
    "thruster_1.b",
    "thruster_2.a", 
    "oxygen_tank_1",
    "hydrogen_tank_1"
]


async def daten_laden():

    cursor = collection.find(
        {
            "name": {
                "$in": komponenten
            }
        },
        {
            "_id": 0,
            "name": 1,
            "timestamp": 1,
            "temperature": 1,
            "pressure": 1
        }
    )

    daten = await cursor.sort(
        "timestamp", 1
    ).limit(100).to_list(length=None)


    ergebnis = {}

    for eintrag in daten:
        name = eintrag["name"]

        if name not in ergebnis:
            ergebnis[name] = []

        ergebnis[name].append({
            "timestamp": eintrag["timestamp"],
            "temperature": eintrag.get("temperature"),
            "pressure": eintrag.get("pressure")
        })

    return ergebnis

if __name__ == "__main__":
    daten = asyncio.run(daten_laden())

    for eintrag in daten:
        print(eintrag)




