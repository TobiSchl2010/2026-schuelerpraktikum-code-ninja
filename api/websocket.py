from fastapi import WebSocket

clients = []


async def connect(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)


async def disconnect(websocket: WebSocket):
    if websocket in clients:
        clients.remove(websocket)


async def send_data(data):
    for client in clients:
        await client.send_json(data)