import uvicorn
import asyncio
from typing import List
import zmq, msgpack
import traceback
import logging
logging.basicConfig(filename='app.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logging.info('starting')

from fastapi import FastAPI, WebSocket, WebSocketException

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()

def readFrame(input):
    [topic, payload] = input.recv_multipart()
    message = msgpack.unpackb(payload, raw=True)
    frame = message[b"message"]
    originatingTime = message[b"originatingTime"]
    return (frame, originatingTime)

input = zmq.Context().socket(zmq.SUB)
input.setsockopt_string(zmq.SUBSCRIBE, u"face-orientation")
input.connect("tcp://127.0.0.1:30002")


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            print(f"[{client_id}] Waiting for zeromq input...")
            frame, originatingTime = readFrame(input)
            print(f"Received from PSI: {frame.decode()}, {originatingTime}")
            message = f"{{\"flag\":{1}, \"message\":\"{frame.decode()}\"}}"
            # if type(eval(message)) == str:
            # if type(message) == str
            await manager.send_personal_message(message, websocket)
            await asyncio.sleep(0.01)

    except Exception as e:
        logging.error(e, exc_info=True, stack_info=True)
        manager.disconnect(websocket)
        print(f"Client #{client_id} left the chat")
        await manager.broadcast(f"Client #{client_id} left the chat")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)