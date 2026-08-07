from fastapi import WebSocket

clients = []


async def connect(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)


async def disconnect(websocket: WebSocket):
    if websocket in clients:
        clients.remove(websocket)


async def send_data(data):
    # Über eine Kopie laufen, weil unten Clients entfernt werden.
    for client in list(clients):
        try:
            await client.send_json(data)

        except Exception:
            # Dieser Browser ist weg (Seite neu geladen, Fenster zu).
            # Ohne dieses try/except würde der Fehler die ganze
            # Sende-Aufgabe beenden - dann bekäme NIEMAND mehr Daten
            # und alle Diagramme würden für immer stehen bleiben.
            await disconnect(client)