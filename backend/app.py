import os
import json
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from core.agent import InvoiceAssistantChatbot

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
CORS(app)

chatbot = InvoiceAssistantChatbot()


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "AI-Powered E-Commerce Invoice Assistant API",
        "ai_provider": "Google Gemini"
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json or {}
        user_message = data.get('message')

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        response = chatbot.process_message(user_message)

        return jsonify({
            "response": response["text"],
            "type": response.get("type", "info"),
            "saved_invoice_id": response.get("saved_invoice_id"),
            "status": "success"
        })

    except Exception as e:
        print(f"Error processing message: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e),
            "hint": "Check if GOOGLE_API_KEY is set in environment variables"
        }), 500


@app.route('/api/invoices', methods=['GET'])
def list_invoices():
    try:
        invoices = chatbot.storage.list_invoices()
        return jsonify({
            "invoices": invoices,
            "count": len(invoices),
            "status": "success"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/invoices/<invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    try:
        invoice = chatbot.storage.get_invoice(invoice_id)
        if invoice:
            return jsonify({"invoice": invoice, "status": "success"})
        return jsonify({"error": "Invoice not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stream-chat', methods=['POST'])
def stream_chat():
    try:
        data = request.json or {}
        user_message = data.get('message')
        session_id = data.get('session_id', 'default')

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        def generate():
            try:
                # Process the message and stream the response
                response = chatbot.process_message(user_message, session_id)

                # Stream the response in chunks
                if isinstance(response, dict):
                    full_response = response.get("response", str(response))
                else:
                    # If response is not a dict, create a proper response format
                    full_response = str(response)
                    response = {"response": full_response, "type": "info"}

                # Simulate streaming by sending response in chunks
                chunk_size = 10  # characters per chunk
                for i in range(0, len(full_response), chunk_size):
                    chunk = full_response[i:i+chunk_size]
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"

                # Send the complete response at the end
                yield f"data: {json.dumps({'complete_response': response, 'done': True})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(generate(), mimetype='text/event-stream')

    except Exception as e:
        print(f"Error processing stream message: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e),
            "hint": "Check if GOOGLE_API_KEY is set in environment variables"
        }), 500


if __name__ == '__main__':
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        print("🚀 AI Invoice Assistant Server running on http://localhost:5000")
        print("✅ Google Gemini API configured")
    else:
        print("🚀 AI Invoice Assistant Server running on http://localhost:5000")
        print("⚠️  WARNING: GOOGLE_API_KEY not set - using fallback regex parser")
    app.run(debug=True, port=5000)
