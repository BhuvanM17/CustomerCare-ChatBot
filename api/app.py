import os
import sys
from flask import Flask, jsonify, request
from flask_cors import CORS

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from backend.core.agent import InvoiceAssistantChatbot

app = Flask(__name__)
CORS(app)
chatbot = InvoiceAssistantChatbot()


@app.get('/api/health')
def health_check():
    return jsonify({"status": "healthy", "service": "AI-Powered E-Commerce Invoice Assistant API"})


@app.post('/api/chat')
def chat():
    data = request.get_json(silent=True) or {}
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    try:
        response_text = chatbot.process_message(user_message)
        return jsonify({"response": response_text, "status": "success"})
    except Exception as error:
        return jsonify({"error": "Internal server error", "details": str(error)}), 500
