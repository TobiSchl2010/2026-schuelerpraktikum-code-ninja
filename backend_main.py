import asyncio

from fastapi import FastAPI, WebSocket

from database.database_access import daten_laden
from api.websocket import connect, disconnect, send_data

app = FastAPI()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket): # Funktion die für jeden neuen Clien ausgeführt wird
    # Verbindung akzeptieren und den Client zur Liste hinzufügen
    await connect(websocket)

    # Solange Streamlit verbunden ist:
    # halte Verbindung offen
    try:
        while True:
            await websocket.receive_text()

    except:
        await disconnect(websocket)


# automatischer Datenlieferant 
async def daten_stream():

    while True:

        daten = await daten_laden()

        print(daten)
        
        await send_data(daten)

        await asyncio.sleep(1)



@app.on_event("startup") # Wenn FastAPI startet, führe diese Funktion aus.
async def startup_event():

    asyncio.create_task(daten_stream())