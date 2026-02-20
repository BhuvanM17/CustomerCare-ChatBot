import os
import re
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import ValidationError

from .models import InvoiceSchema, InvoiceItem, ConversationHistory, ConversationMessage
from ..scripts.generate_invoice_pdf import create_invoice_pdf
from .rag_system import get_faq_answer
from .llm_manager import generate_with_fallback

load_dotenv()

# Configure Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)


class InvoiceDraft:
    def __init__(self, invoice_schema: InvoiceSchema = None):
        if invoice_schema:
            self.schema_obj = invoice_schema
        else:
            self.schema_obj = InvoiceSchema()

    @property
    def invoice_id(self) -> str:
        return self.schema_obj.invoice_id

    @property
    def invoice_number(self) -> Optional[str]:
        return self.schema_obj.invoice_number

    @property
    def customer_name(self) -> Optional[str]:
        return self.schema_obj.customer_name

    @property
    def customer_email(self) -> Optional[str]:
        return self.schema_obj.customer_email

    @property
    def customer_gst(self) -> Optional[str]:
        return self.schema_obj.customer_gst

    @property
    def invoice_date(self) -> Optional[str]:
        return self.schema_obj.invoice_date

    @property
    def due_date(self) -> Optional[str]:
        return self.schema_obj.due_date

    @property
    def currency(self) -> str:
        return self.schema_obj.currency

    @property
    def tax_percent(self) -> float:
        return self.schema_obj.tax_percent

    @property
    def shipping_fee(self) -> float:
        return self.schema_obj.shipping_fee

    @property
    def discount(self) -> float:
        return self.schema_obj.discount

    @property
    def discount_code(self) -> Optional[str]:
        return self.schema_obj.discount_code

    @property
    def items(self) -> List[InvoiceItem]:
        return self.schema_obj.items

    @invoice_number.setter
    def invoice_number(self, value: Optional[str]):
        self.schema_obj.invoice_number = value

    @customer_name.setter
    def customer_name(self, value: Optional[str]):
        self.schema_obj.customer_name = value

    @customer_email.setter
    def customer_email(self, value: Optional[str]):
        self.schema_obj.customer_email = value

    @customer_gst.setter
    def customer_gst(self, value: Optional[str]):
        self.schema_obj.customer_gst = value

    @invoice_date.setter
    def invoice_date(self, value: Optional[str]):
        self.schema_obj.invoice_date = value

    @due_date.setter
    def due_date(self, value: Optional[str]):
        self.schema_obj.due_date = value

    @tax_percent.setter
    def tax_percent(self, value: float):
        self.schema_obj.tax_percent = value

    @shipping_fee.setter
    def shipping_fee(self, value: float):
        self.schema_obj.shipping_fee = value

    @discount.setter
    def discount(self, value: float):
        self.schema_obj.discount = value

    @discount_code.setter
    def discount_code(self, value: Optional[str]):
        self.schema_obj.discount_code = value

    @items.setter
    def items(self, value: List[InvoiceItem]):
        self.schema_obj.items = value

    def to_dict(self):
        return self.schema_obj.to_dict()


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, InvoiceDraft] = {}
        self.conversations: Dict[str, ConversationHistory] = {}

    def get_draft(self, session_id: str) -> InvoiceDraft:
        if session_id not in self.sessions:
            self.sessions[session_id] = InvoiceDraft()
        return self.sessions[session_id]

    def get_conversation_history(self, session_id: str) -> ConversationHistory:
        if session_id not in self.conversations:
            self.conversations[session_id] = ConversationHistory(
                session_id=session_id)
        return self.conversations[session_id]

    def add_message_to_conversation(self, session_id: str, message: ConversationMessage):
        history = self.get_conversation_history(session_id)
        history.add_message(message)
        self.conversations[session_id] = history

    def get_recent_messages(self, session_id: str, limit: int = 5) -> List[ConversationMessage]:
        history = self.get_conversation_history(session_id)
        return history.messages[-limit:] if len(history.messages) >= limit else history.messages

    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.conversations:
            del self.conversations[session_id]


class InvoiceStorage:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        # Vercel compatibility: Use /tmp if running on Vercel to avoid read-only filesystem errors
        if os.environ.get("VERCEL"):
            tmp_path = os.path.join("/tmp", "invoices.json")
            print(f"📡 Vercel detected. Redirecting storage to: {tmp_path}")
            self.storage_path = tmp_path

        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def _load_invoices(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    return json.load(f)
            except:
                pass
        return []

    def save_invoice(self, draft: InvoiceDraft):
        invoices = self._load_invoices()
        invoice_data = draft.to_dict()
        invoices.append(invoice_data)
        with open(self.storage_path, "w") as f:
            json.dump(invoices, f, indent=4)

        # Generate PDF for the invoice
        try:
            pdf_path = create_invoice_pdf(
                invoice_data,
                f"invoice_{draft.invoice_number or draft.invoice_id[:8]}.pdf"
            )
            print(f"📄 Invoice PDF generated: {pdf_path}")
        except Exception as e:
            print(f"⚠️  Could not generate PDF: {e}")

        return draft.invoice_id

    def list_invoices(self):
        return self._load_invoices()

    def get_invoice(self, invoice_id):
        invoices = self._load_invoices()
        for invoice in invoices:
            if invoice.get('invoice_id') == invoice_id or (invoice.get('invoice_number') and invoice.get('invoice_number') == invoice_id):
                return invoice
        return None


class InvoiceParser:
    def __init__(self, session_manager, model_name="gemini-2.5-flash"):
        self.model = genai.GenerativeModel(model_name)
        self.sessions = session_manager

    def update_draft(self, draft: InvoiceDraft, text: str, session_id: str = "default") -> InvoiceDraft:
        # Get recent conversation history to provide context
        recent_messages = self.get_recent_messages_for_context(session_id)

        current_data = draft.to_dict()
        prompt = f"""
        You are an AI assistant that extracts invoice details from user messages. 
        Update the current invoice data with new information from the user's text.
        
        Current Invoice Data: {json.dumps(current_data, indent=2)}
        
        Recent Conversation Context:
        {recent_messages}
        
        User Message: "{text}"
        
        INSTRUCTIONS:
        1. If user provides a name, update 'customer_name'.
        2. If user provides an email, update 'customer_email'.
        3. If items are mentioned, ADD them to the existing items list or update quantities if same item.
        4. If GST/Tax is mentioned, update 'customer_gst' or 'tax_percent'.
        5. If a discount/offer/coupon is mentioned, update 'discount_code' or 'discount'.
        6. Parse quantities properly (e.g., '3 shirts' means quantity=3)
        7. Parse prices properly (e.g., '@ 2499' means unit_price=2499)
        8. Return ONLY the complete updated JSON object matching the structure below.
        
        JSON Structure:
        {{
            "invoice_number": string | null,
            "customer_name": string | null,
            "customer_email": string | null,
            "customer_gst": string | null,
            "currency": string,
            "tax_percent": number,
            "shipping_fee": number,
            "discount": number,
            "discount_code": string | null,
            "items": [
                {{"name": string, "quantity": number, "unit_price": number}}
            ]
        }}
        """
        try:
            response = self.model.generate_content(prompt)

            # Extract JSON from response
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                extracted_data = json.loads(match.group())

                # Prepare data for validation
                validated_data = {
                    "invoice_number": extracted_data.get('invoice_number', draft.invoice_number),
                    "customer_name": extracted_data.get('customer_name', draft.customer_name),
                    "customer_email": extracted_data.get('customer_email', draft.customer_email),
                    "customer_gst": extracted_data.get('customer_gst', draft.customer_gst),
                    "currency": extracted_data.get('currency', draft.currency),
                    "tax_percent": extracted_data.get('tax_percent', draft.tax_percent),
                    "shipping_fee": extracted_data.get('shipping_fee', draft.shipping_fee),
                    "discount": extracted_data.get('discount', draft.discount),
                    "discount_code": extracted_data.get('discount_code', draft.discount_code),
                    "items": []
                }

                # Handle items separately since we want to merge/add them rather than replace
                existing_items = [item.dict() for item in draft.items]
                new_items = extracted_data.get('items', [])

                # Merge new items with existing ones
                merged_items = existing_items.copy()
                for new_item in new_items:
                    # Check if this item already exists (same name)
                    found = False
                    for i, existing_item in enumerate(merged_items):
                        if existing_item['name'].lower() == new_item['name'].lower():
                            # Update quantity if same item
                            merged_items[i]['quantity'] += new_item['quantity']
                            merged_items[i]['unit_price'] = new_item['unit_price']
                            found = True
                            break
                    if not found:
                        merged_items.append(new_item)

                validated_data['items'] = merged_items

                # Validate with Pydantic model
                invoice_schema = InvoiceSchema(**validated_data)

                # Create new draft with validated data
                draft = InvoiceDraft(invoice_schema)

                # Set dates if not already set
                if not draft.invoice_date:
                    draft.invoice_date = datetime.now().strftime("%Y-%m-%d")
                if not draft.due_date:
                    draft.due_date = (
                        datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        except ValidationError as ve:
            print(f"Validation error: {ve}")
            # Fallback to original logic if validation fails
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                if 'items' in data:
                    draft.items = [InvoiceItem(**item)
                                   for item in data['items']]
                draft.invoice_number = data.get(
                    'invoice_number', draft.invoice_number)
                draft.customer_name = data.get(
                    'customer_name', draft.customer_name)
                draft.customer_email = data.get(
                    'customer_email', draft.customer_email)
                draft.customer_gst = data.get(
                    'customer_gst', draft.customer_gst)
                draft.tax_percent = data.get('tax_percent', draft.tax_percent)
                draft.shipping_fee = data.get(
                    'shipping_fee', draft.shipping_fee)
                draft.discount = data.get('discount', draft.discount)
                draft.discount_code = data.get(
                    'discount_code', draft.discount_code)

                if not draft.invoice_date:
                    draft.invoice_date = datetime.now().strftime("%Y-%m-%d")
                if not draft.due_date:
                    draft.due_date = (
                        datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        except Exception as e:
            print(f"Error parsing: {e}")
        return draft

    def get_recent_messages_for_context(self, session_id: str) -> str:
        """Get recent messages to provide context for the LLM"""
        try:
            recent_msgs = self.sessions.get_recent_messages(session_id, 5)
            context = []
            for msg in recent_msgs:
                sender = 'User' if msg.sender == 'user' else 'Assistant'
                context.append(f"{sender}: {msg.text}")
            return '\n'.join(context) if context else "No recent conversation history."
        except:
            return "No recent conversation history."


class InvoiceEngine:
    REQUIRED_FIELDS = ["customer_name", "customer_email"]

    def validate(self, draft: InvoiceDraft) -> List[str]:
        missing = []
        if not draft.customer_name:
            missing.append("customer_name")
        if not draft.customer_email:
            missing.append("customer_email")
        if not draft.items:
            missing.append("items")
        return missing

    def suggestions(self, draft: InvoiceDraft) -> List[str]:
        tips = []
        if not draft.customer_name:
            tips.append("What is the customer's name?")
        if not draft.customer_email:
            tips.append("Could you provide their email address?")
        if not draft.customer_gst:
            tips.append(
                "Do you have a GST number to include? (Optional but recommended)")
        if not draft.discount_code:
            tips.append("Do you have any discount codes or offers to apply?")
        return tips

    def render_invoice(self, draft: InvoiceDraft) -> str:
        data = draft.to_dict()
        lines = [
            f"🧾 **Invoice {draft.invoice_number or 'DRAFT'}**",
            f"**Customer:** {draft.customer_name}",
            f"**Email:** {draft.customer_email}",
            f"**GSTIN:** {draft.customer_gst or 'Not Provided'}",
            f"**Date:** {draft.invoice_date}",
            "", "**Line Items**"
        ]
        for item in draft.items:
            lines.append(
                f"• {item.name} — {item.quantity:g} × {item.unit_price:.2f} = {item.line_total:.2f}")

        lines.extend([
            "",
            f"**Subtotal:** ₹{data['subtotal']:.2f}",
            f"**GST ({draft.tax_percent:g}%):** ₹{data['tax_amount']:.2f}",
            f"**Shipping:** ₹{draft.shipping_fee:.2f}",
            f"**Discount:** -₹{data['discount']:.2f} {f'({draft.discount_code})' if draft.discount_code else ''}",
            f"✅ **Grand Total:** ₹{data['grand_total']:.2f}"
        ])
        return "\n".join(lines)


class InvoiceAssistantChatbot:
    def __init__(self):
        self.sessions = SessionManager()
        self.parser = InvoiceParser(self.sessions)
        self.engine = InvoiceEngine()
        storage_path = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "data", "invoices.json")
        self.storage = InvoiceStorage(storage_path)

    def process_message(self, user_message: str, session_id: str = "default") -> Dict[str, Any]:
        msg = user_message.lower()
        draft = self.sessions.get_draft(session_id)

        # Add user message to conversation history
        user_msg = ConversationMessage(text=user_message, sender='user')
        self.sessions.add_message_to_conversation(session_id, user_msg)

        # Detect intent to start or continue an invoice
        is_invoice_talk = any(kw in msg for kw in [
                              "invoice", "bill", "checkout", "to raju", "@", "gmail", "com", "gst"])

        if is_invoice_talk or draft.items:
            draft = self.parser.update_draft(draft, user_message, session_id)
            missing = self.engine.validate(draft)

            if missing:
                suggestions = self.engine.suggestions(draft)
                text = (
                    "I've updated your draft, but I'm still missing some details:\n\n"
                    + "\n".join(f"• {tip}" for tip in suggestions)
                    + "\n\nJust type them in and I'll update the bill!"
                )
                # Add bot response to conversation history
                bot_msg = ConversationMessage(
                    text=text, sender='bot', type="warning")
                self.sessions.add_message_to_conversation(session_id, bot_msg)
                return {"text": text, "type": "warning"}

            # If all required fields are here, and it's the first time we have them all, or they say "confirm"
            if not missing:
                # auto-generate or ask to confirm?
                # The user wants "python script should be run to create an invoice for that"
                # so we generate and save.
                invoice_id = self.storage.save_invoice(draft)
                text = "### 🚀 Invoice Generated Successfully!\n\n" + \
                    self.engine.render_invoice(draft)
                # Add bot response to conversation history
                bot_msg = ConversationMessage(
                    text=text, sender='bot', type="invoice")
                self.sessions.add_message_to_conversation(session_id, bot_msg)
                self.sessions.clear_session(session_id)  # Reset for next one
                return {"text": text, "type": "invoice", "saved_invoice_id": invoice_id}

        # Fallback to general assistant
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(
                f"User: {user_message}. Act as UrbanStyle Shopping Assistant. If they want to bill or checkout, guide them.")
            # Add bot response to conversation history
            bot_msg = ConversationMessage(
                text=response.text, sender='bot', type="info")
            self.sessions.add_message_to_conversation(session_id, bot_msg)
            return {"text": response.text, "type": "info"}
        except:
            bot_response = "How can I help you shop today?"
            bot_msg = ConversationMessage(
                text=bot_response, sender='bot', type="info")
            self.sessions.add_message_to_conversation(session_id, bot_msg)
            return {"text": bot_response, "type": "info"}


BizzHubChatbot = InvoiceAssistantChatbot
