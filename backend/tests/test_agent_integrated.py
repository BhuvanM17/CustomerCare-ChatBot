import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to import core.agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import InvoiceAssistantChatbot

def test_chatbot_parsing():
    load_dotenv()
    if not os.getenv("GOOGLE_API_KEY"):
        print("⏭️ Skipping test: GOOGLE_API_KEY not set.")
        return

    chatbot = InvoiceAssistantChatbot()
    
    test_message = "Generate invoice: INV-2026-X for John Doe (john@example.com), 2x Coffee Beans @ 450, 1x Grinder @ 1200, tax 18%, shipping 50"
    
    print(f"Testing with message: {test_message}")
    response = chatbot.process_message(test_message)
    
    print("\n--- Bot Response ---")
    print(f"Type: {response['type']}")
    print(f"Text:\n{response['text']}")
    print(f"Saved Invoice ID: {response.get('saved_invoice_id')}")
    
    if response['type'] == 'invoice' and response.get('saved_invoice_id'):
        print("\n✅ Integrated Test Passed: Invoice generated and saved.")
    else:
        print("\n❌ Integrated Test Failed: Response was not an invoice or wasn't saved.")

if __name__ == "__main__":
    test_chatbot_parsing()
