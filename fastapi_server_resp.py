import uvicorn
import asyncio
from typing import List, Dict
import logging
from zmq_utils import *
logging.basicConfig(filename='app_fp_resp.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logging.info('starting')

from fastapi import FastAPI, WebSocket

app = FastAPI()

class ConnectionManager:
    # fp - fastapi
    # fe - frontend
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {"fe2fp_tts_updates": [], "fe2fp_code": [], "fp2fe_responses": []}

    async def connect(self, websocket: WebSocket, key:str):
        await websocket.accept()
        self.active_connections[key].append(websocket)

    def disconnect(self, websocket: WebSocket, key:str):
        self.active_connections[key].remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, key:str):
        for connection in self.active_connections[key]:
            await connection.send_text(message)


manager = ConnectionManager()

input_sock = zmq.Context().socket(zmq.SUB)
input_sock.setsockopt_string(zmq.SUBSCRIBE, u"face-orientation")
input_sock.connect("tcp://127.0.0.1:40002")


@app.websocket("/ws/fp_resp/{client_id}")
async def websocket_chatgpt_resp(websocket: WebSocket, client_id: int):
    key = "fp2fe_responses"
    await manager.connect(websocket, key)
    try:
        while True:

            # waiting for input from psi to send to fe
            print(f"[{client_id}] Waiting for zeromq input...")
            frame, originatingTime = readFrame(input_sock)
            print(f"Received from PSI: {frame.decode()}, {originatingTime}")
            message = f"{{\"flag\":{1}, \"message\":\"{frame.decode()}\"}}"
            await manager.send_personal_message(message, websocket)
            
            await asyncio.sleep(0.01)

    except Exception as e:
        logging.error(e, exc_info=True, stack_info=True)
        manager.disconnect(websocket, key)
        print(f"Client #{client_id} left the chat")
        await manager.broadcast(f"Client #{client_id} left the chat", key)