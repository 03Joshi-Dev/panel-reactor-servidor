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
from flask_cors import CORS

# --- CONFIGURACIÓN DE LA APP ---
app = Flask(__name__)
sock = Sock(app)

cors = CORS(app, resources={
    r"/*": {
        "origins": [
            "http://127.0.0.1:3000",
            "https://03joshi-dev.github.io"
        ]
    }
})

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

        missing_padding = len(encoded) % 4
        if missing_padding:
            encoded += '=' * (4 - missing_padding)
        
        pdf_data = base64.b64decode(encoded)
        
        part = MIMEBase("application", "octet-stream")
        part.set_payload(pdf_data)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename=checklist.pdf")
        message.attach(part)
    except Exception as e:
        print(f"Error CRÍTICO al procesar el PDF adjunto: {e}")
        return False

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        print("Correo enviado exitosamente.")
        return True
    except Exception as e:
        print(f"Error CRÍTICO al enviar el correo: {e}")
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
    try:
        data = request.json
        print(f"Dato recibido: {data}")
        for client in list(connected_clients):
            try:
                client.send(json.dumps(data))
            except:
                connected_clients.remove(client)
        return jsonify({"status": "ok"}), 200
    except:
        return jsonify({"status": "error"}), 400

@sock.route('/')
def websocket_connection(ws):
    connected_clients.append(ws)
    try:
        while True: ws.receive()
    except: pass
    finally:
        if ws in connected_clients: connected_clients.remove(ws)

@app.route('/')
def index():
    return "Servidor del reactor activo."

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
