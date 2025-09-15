
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
        # Enviar los datos a todos los clientes web conectados
        # Se crea una copia de la lista por si un cliente se desconecta mientras se envía
        for client in list(connected_clients):
            try:
                client.send(json.dumps(data))
            except Exception as e:
                print(f"No se pudo enviar a un cliente (probablemente desconectado): {e}")
                connected_clients.remove(client) # Limpiar cliente desconectado
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"Error en /data: {e}")
        return jsonify({"status": "error"}), 400

# Endpoint WebSocket que se ejecuta cuando la página web se conecta
# La librería flask_sock se encarga de la magia
@sock.route('/')
def websocket_connection(ws):
    print("Nuevo cliente web conectado.")
    connected_clients.append(ws)
    try:
        # Mantener la conexión viva esperando mensajes (aunque no hagamos nada con ellos)
        while True:
            # Esta línea espera a que el cliente envíe algo o se desconecte.
            # Si se desconecta, lanzará una excepción y el bloque 'finally' se ejecutará.
            ws.receive()
    except Exception as e:
        print(f"Cliente desconectado o error: {e}")
    finally:
        # Eliminar el cliente de la lista cuando la conexión se cierra
        if ws in connected_clients:
            connected_clients.remove(ws)
        print("Un cliente se ha desconectado. Clientes activos:", len(connected_clients))

# Ruta de prueba para ver si el servidor HTTP está funcionando
@app.route('/')
def index():
    return "Servidor del reactor activo. El WebSocket está en la misma dirección."

# Esta parte no es necesaria para Render, pero la dejamos por si lo ejecutas localmente
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    print(f"Iniciando servidor en el puerto {port}...")
    # Para pruebas locales, necesitarías un servidor como gunicorn.
    # Pero para Render, el 'Start Command' se encargará de esto.
    app.run(host='0.0.0.0', port=port)
