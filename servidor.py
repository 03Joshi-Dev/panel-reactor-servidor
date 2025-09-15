import os
import json
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import base64

from flask import Flask, request, jsonify
from flask_sock import Sock
from flask_cors import CORS # <--- 1. IMPORTAR LA LIBRERÍA

# --- CONFIGURACIÓN DE LA APP ---
app = Flask(__name__)
sock = Sock(app)
CORS(app)

# Almacenará las conexiones WebSocket activas
connected_clients = []

# --- LÓGICA DE ENVÍO DE CORREO ---
def send_email_with_attachment(subject, pdf_data_string):
    sender_email = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASS')
    receiver_email = "jaimesjorge0320@gmail.com"

    if not sender_email or not password:
        print("ERROR: Las variables de entorno EMAIL_USER o EMAIL_PASS no están configuradas.")
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email
    message.attach(MIMEText("Checklist del reactor adjunto en formato PDF.", "plain"))

    try:
        header, encoded = pdf_data_string.split(",", 1)
        pdf_data = base64.b64decode(encoded)
        
        part = MIMEBase("application", "octet-stream")
        part.set_payload(pdf_data)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename=checklist.pdf")
        message.attach(part)
    except Exception as e:
        print(f"Error al procesar el PDF adjunto: {e}")
        return False

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        print("Correo enviado exitosamente.")
        return True
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        return False

# --- ENDPOINTS (RUTAS) DEL SERVIDOR ---

# NUEVO ENDPOINT PARA RECIBIR Y ENVIAR EL CHECKLIST
@app.route('/enviar-checklist', methods=['POST'])
def handle_send_checklist():
    data = request.json
    pdf_data = data.get('pdf_data')
    subject = data.get('subject')

    if not pdf_data or not subject:
        return jsonify({"status": "error", "message": "Faltan datos en la petición"}), 400

    success = send_email_with_attachment(subject, pdf_data)
    
    if success:
        return jsonify({"status": "ok", "message": "Correo enviado."}), 200
    else:
        return jsonify({"status": "error", "message": "Fallo en el servidor al enviar el correo."}), 500

# ENDPOINT PARA RECIBIR DATOS DEL REACTOR
@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.json
        print(f"Dato recibido: {data}")
        for client in list(connected_clients):
            try:
                client.send(json.dumps(data))
            except Exception as e:
                print(f"Cliente desconectado detectado, eliminando. Error: {e}")
                connected_clients.remove(client)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"Error procesando la petición en /data: {e}")
        return jsonify({"status": "error"}), 400

# ENDPOINT WEBSOCKET PARA LA PÁGINA WEB
@sock.route('/')
def websocket_connection(ws):
    print("Nuevo cliente web conectado.")
    connected_clients.append(ws)
    try:
        while True:
            ws.receive()
    except Exception as e:
        print(f"Cliente desconectado o con error: {e}")
    finally:
        if ws in connected_clients:
            connected_clients.remove(ws)
        print(f"Un cliente se ha desconectado. Clientes activos: {len(connected_clients)}")

# RUTA DE PRUEBA
@app.route('/')
def index():
    return "Servidor del reactor activo."

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
