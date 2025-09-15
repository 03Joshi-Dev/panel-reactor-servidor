from flask import Flask, request, jsonify
from flask_sock import Sock
import json
import os

app = Flask(__name__)
sock = Sock(app)

# Esta lista almacenará todas las conexiones WebSocket activas
connected_clients = []

# Endpoint HTTP para que el recolector.py envíe los datos
@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.json
        print(f"Dato recibido: {data}")

        # =======================================================
        # CORRECCIÓN: Lógica de envío más robusta
        # =======================================================
        # Creamos una copia de la lista para poder modificar la original mientras iteramos
        for client in list(connected_clients):
            try:
                # Intentamos enviar el dato
                client.send(json.dumps(data))
            except Exception as e:
                # Si falla, es porque el cliente se desconectó.
                # Lo eliminamos de la lista y continuamos con los demás.
                print(f"Cliente desconectado detectado, eliminando. Error: {e}")
                connected_clients.remove(client)
        # =======================================================

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"Error procesando la petición en /data: {e}")
        return jsonify({"status": "error"}), 400

# Endpoint WebSocket que se ejecuta cuando la página web se conecta
@sock.route('/')
def websocket_connection(ws):
    print("Nuevo cliente web conectado.")
    connected_clients.append(ws)
    try:
        # Mantenemos la conexión viva esperando mensajes (aunque no hagamos nada con ellos)
        while True:
            # Esta línea espera a que el cliente envíe algo o se desconecte.
            # Si se desconecta, lanzará una excepción y el bloque 'finally' se ejecutará.
            message = ws.receive()
            print(f"Mensaje recibido de un cliente (se ignorará): {message}")
    except Exception as e:
        print(f"Cliente desconectado o con error: {e}")
    finally:
        # Eliminar el cliente de la lista cuando la conexión se cierra
        if ws in connected_clients:
            connected_clients.remove(ws)
        print(f"Un cliente se ha desconectado. Clientes activos: {len(connected_clients)}")

# Ruta de prueba para ver si el servidor HTTP está funcionando
@app.route('/')
def index():
    return "Servidor del reactor activo. El WebSocket está en la misma dirección."

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    print(f"Iniciando servidor en el puerto {port}...")
    # Para producción, es mejor usar un servidor WSGI como Gunicorn.
    # El 'Start Command' en Render se encargará de esto.
    app.run(host='0.0.0.0', port=port)
