from flask import Flask, request, jsonify
from flask_cors import CORS
from core.agent import InvoiceAssistantChatbot

app = Flask(__name__)
CORS(app)

chatbot = InvoiceAssistantChatbot()


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "AI-Powered E-Commerce Invoice Assistant API"})


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json or {}
        user_message = data.get('message')

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        response_text = chatbot.process_message(user_message)

        return jsonify({
            "response": response_text,
            "status": "success"
        })

    except Exception as e:
        print(f"Error processing message: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


if __name__ == '__main__':
    print("🚀 AI Invoice Assistant Server running on http://localhost:5000")
    app.run(debug=True, port=5000)
