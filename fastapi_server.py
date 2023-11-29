import asyncio
from typing import List, Dict
import json
import logging
from zmq_utils import *
logging.basicConfig(filename='app_fe_resp.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
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

output_sock = create_socket(ip_address="tcp://*:41000")

@app.websocket("/ws/fe_tts/{client_id}")
async def websocket_tts_updates(websocket: WebSocket, client_id: int):
    key = "fe2fp_tts_updates"
    await manager.connect(websocket, key)
    try:
        while True:
            # waiting from fe, when it says a text or "hello I am rachel", to send to psi
            data = await websocket.receive_text()
            print(f"Message received from FE {data}")
            send_payload(output_sock, "fe-tts", data, originatingTime=None)

            await asyncio.sleep(0.01)

    except Exception as e:
        logging.error(e, exc_info=True, stack_info=True)
        manager.disconnect(websocket, key)
        print(f"Client #{client_id} left the chat")
        # await manager.broadcast(f"Client #{client_id} left the chat", key)
    
@app.websocket("/ws/fe_code/{client_id}")
async def websocket_code_updates(websocket: WebSocket, client_id: int):
    key = "fe2fp_code"
    await manager.connect(websocket, key)
    try:
        while True:
            # waiting from fe, when it says a text or "hello I am rachel", to send to psi
            data = await websocket.receive_text()
            print(f"Code received from FE {data}")
            send_payload(output_sock, "fe-code", data, originatingTime=None)
            await asyncio.sleep(0.01)

    except Exception as e:
        logging.error(e, exc_info=True, stack_info=True)
        manager.disconnect(websocket, key)
        print(f"Client #{client_id} left the code support")

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8081, workers=4)