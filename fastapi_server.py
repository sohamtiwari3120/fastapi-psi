import uvicorn
import asyncio
from typing import List
import traceback
import json
import logging
from zmq_utils import *
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


input = zmq.Context().socket(zmq.SUB)
input.setsockopt_string(zmq.SUBSCRIBE, u"face-orientation")
input.connect("tcp://127.0.0.1:40002")

output_sock = create_socket(ip_address="tcp://*:41000")

# input2 = zmq.Context().socket(zmq.SUB)
# input2.setsockopt_string(zmq.SUBSCRIBE, u"agent-response")
# input2.connect("tcp://127.0.0.1:30002")


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            # waiting from fe, when it says a text or "hello I am rachel", to send to psi
            print(f"Waitingg for FE")
            data = await websocket.receive_text()
            try:
                data = json.loads(data)
            except Exception as e:
                logging.error(e, exc_info=True, stack_info=True)
            print(type(data), data)
            print(f"Message received from FE {data}")
            send_payload(output_sock, "fe-tts", data, originatingTime=None)

            # waiting for input from psi to send to fe
            print(f"[{client_id}] Waiting for zeromq input...")
            frame, originatingTime = await readFrame(input)
            print(f"Received from PSI: {frame.decode()}, {originatingTime}")
            message = f"{{\"flag\":{1}, \"message\":\"{frame.decode()}\"}}"
            # message = f"{{\"flag\":{1}, \"message\":\"{'alright alright alright'}\"}}"
            # frame, originatingTime = readFrame(input2)
            # print(f"Received from PSI (agent response): {frame.decode()}, {originatingTime}")
            # message2 = f"{{\"flag\":{1}, \"message\":\"{frame.decode()}\"}}"
            # if type(eval(message)) == str:
            # if type(message) == str
            await manager.send_personal_message(message, websocket)
            
            await asyncio.sleep(0.01)

    except Exception as e:
        logging.error(e, exc_info=True, stack_info=True)
        manager.disconnect(websocket)
        print(f"Client #{client_id} left the chat")
        await manager.broadcast(f"Client #{client_id} left the chat")
    
@app.websocket("/ws2/{client_id}")
async def websocket_endpoint2(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            # waiting from fe, when it says a text or "hello I am rachel", to send to psi
            data = await websocket.receive_text()
            print(f"Code received from FE {data}")
            await asyncio.sleep(0.01)

    except Exception as e:
        logging.error(e, exc_info=True, stack_info=True)
        manager.disconnect(websocket)
        print(f"Client #{client_id} left the code support")
        await manager.broadcast(f"Client #{client_id} left the code support")

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8081, workers=4)