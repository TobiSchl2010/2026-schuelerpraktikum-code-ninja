import asyncio
import websockets


async def main():

    uri = "ws://localhost:8000/ws"

    async with websockets.connect(uri) as websocket:

        print("WebSocket verbunden")

        while True:
            daten = await websocket.recv()
            print(daten)


asyncio.run(main())