import os
import json
import asyncio
import threading
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from flask import Flask, request, jsonify
from flask_sock import Sock

# --- CONFIGURACIÓN DE LA APP ---
app = Flask(__name__)
sock = Sock(app)
connected_clients = []

# --- LÓGICA DE ENVÍO DE CORREO ---
def send_email_with_attachment(subject, pdf_data_string):
    sender_email = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASS')
    receiver_email = "jaimesjorge0320@gmail.com"

    if not sender_email or not password:
        print("ERROR: Las variables de entorno EMAIL_USER o EMAIL_PASS no están configuradas.")
        return False

    # Crear el correo
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email
    message.attach(MIMEText("Checklist del reactor adjunto en formato PDF.", "plain"))

    # Procesar el PDF adjunto (viene como un string Base64)
    try:
        # Extraer los datos base64 del string
        header, encoded = pdf_data_string.split(",", 1)
        pdf_data =_data
        
        part = MIMEBase("application", "octet-stream")
        part.set_payload(pdf_data)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename=checklist.pdf")
        message.attach(part)
    except Exception as e:
        print(f"Error al procesar el PDF adjunto: {e}")
        return False

    # Enviar el correo usando el servidor de Gmail
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

@app.route('/enviar-checklist', methods=['POST'])
def handle_send_checklist():
    data = request.json
    pdf_data = data.get('pdf_data')
    subject = data.get('subject')

    if not pdf_data or not subject:
        return jsonify({"status": "error", "message": "Faltan datos"}), 400

    success = send_email_with_attachment(subject, pdf_data)
    
    if success:
        return jsonify({"status": "ok", "message": "Correo enviado."}), 200
    else:
        return jsonify({"status": "error", "message": "Fallo en el envío del correo."}), 500

@app.route('/data', methods=['POST'])
def receive_data():
    data = request.json
    print(f"Dato recibido: {data}")
    asyncio.run(broadcast_data(data))
    return jsonify({"status": "ok"}), 200

@sock.route('/')
def websocket_connection(ws):
    print("Nuevo cliente web conectado.")
    connected_clients.append(ws)
    try:
        while True:
            ws.receive()
    except Exception:
        pass
    finally:
        if ws in connected_clients:
            connected_clients.remove(ws)
        print("Un cliente se ha desconectado.")

async def broadcast_data(data):
    if connected_clients:
        message = json.dumps(data)
        await asyncio.gather(*(client.send(message) for client in list(connected_clients) if not client.closed))

def run_websocket_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    start_server = websockets.serve(register, "0.0.0.0", 8765, loop=loop)
    loop.run_until_complete(start_server)
    loop.run_forever()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
