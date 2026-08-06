import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect

from api.websocket import connect, disconnect, send_data
from database.database_access import daten_laden
from generator.DataGenerator import DataGenerator
from processing.processing import process_json_folder

# Skript nicht mit "Play" starten, deenn ein FastAPI-Code läuft nicht von alleine. Er ist wie ein Motor, der einen Anlasser braucht – und dieser Anlasser heißt Uvicorn. uvicorn main:app --reload
generator = DataGenerator()

@asynccontextmanager  
async def lifespan(app: FastAPI):
    # Diese Tasks starten jetzt garantiert beim Server-Start
    asyncio.create_task(generate_json_data())
    asyncio.create_task(process_json_data())
    asyncio.create_task(daten_stream())
    yield

# Hier erstellen wir die App einmalig und richtig mit dem Lifespan
app = FastAPI(lifespan=lifespan)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connect(websocket)

    try:
        while True:
            # Verbindung offen halten
            await asyncio.sleep(3600)

    except WebSocketDisconnect:
        print("Client hat die WebSocket-Verbindung getrennt.")

    except Exception as e:
        print(f"Unerwarteter Fehler im WebSocket: {e}")

    finally:
        await disconnect(websocket)

async def generate_json_data():
    while True:
        data = generator.generate_new_sensor_data()
        generator.store_sensor_data(data)
        print(f"JSON gespeichert: {data.name}")
        await asyncio.sleep(2)

async def process_json_data():
    while True:
        await process_json_folder("data")
        print("JSON verarbeitet")
        await asyncio.sleep(2)

async def daten_stream():
    while True:
        daten = await daten_laden()
        await send_data(daten)
        await asyncio.sleep(1)

# uvicorn main:app --reload