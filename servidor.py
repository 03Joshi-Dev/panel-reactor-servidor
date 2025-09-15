# nombre del archivo: servidor.py

from flask import Flask, request, jsonify
import asyncio
import websockets
import json
import threading
import os

app = Flask(__name__)
connected_clients = set()

# Lógica para manejar clientes WebSocket
async def register(websocket):
    print("Nuevo cliente web conectado.")
    connected_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        print("Cliente web desconectado.")
        connected_clients.remove(websocket)

async def broadcast_data(data):
    if connected_clients:
        message = json.dumps(data)
        # Enviar a todos los clientes conectados
        await asyncio.gather(*(client.send(message) for client in connected_clients))

# Endpoint HTTP para recibir datos del Arduino (vía recolector.py)
@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.json
        print(f"Dato recibido: {data}")
        # Llama a la función asíncrona para retransmitir los datos
        asyncio.run(broadcast_data(data))
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"Error recibiendo datos: {e}")
        return jsonify({"status": "error"}), 400
        
@app.route('/')
def index():
    return "Servidor del reactor activo. El WebSocket está en el puerto 8765."

# Función para que el servidor WebSocket corra en un hilo separado
def run_websocket_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    start_server = websockets.serve(register, "0.0.0.0", 8765)
    loop.run_until_complete(start_server)
    print("Servidor WebSocket escuchando en el puerto 8765")
    loop.run_forever()

if __name__ == "__main__":
    print("Iniciando servidor Flask y WebSocket...")
    ws_thread = threading.Thread(target=run_websocket_server)
    ws_thread.daemon = True
    ws_thread.start()
    
    # Render usa la variable de entorno PORT, pero definimos 10000 como fallback
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)