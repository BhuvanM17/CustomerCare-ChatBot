import os
import re
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

@dataclass
class InvoiceItem:
    name: str
    quantity: float
    unit_price: float

    @property
    def line_total(self) -> float:
        return round(self.quantity * self.unit_price, 2)

@dataclass
class InvoiceDraft:
    invoice_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    invoice_number: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_gst: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: str = "INR"
    tax_percent: float = 18.0  # Default GST for many items
    shipping_fee: float = 0.0
    discount: float = 0.0
    discount_code: Optional[str] = None
    items: List[InvoiceItem] = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d['subtotal'] = round(sum(item.line_total for item in self.items), 2)
        d['tax_amount'] = round(d['subtotal'] * (self.tax_percent / 100), 2)
        d['grand_total'] = round(d['subtotal'] + d['tax_amount'] + self.shipping_fee - self.discount, 2)
        return d

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, InvoiceDraft] = {}

    def get_draft(self, session_id: str) -> InvoiceDraft:
        if session_id not in self.sessions:
            self.sessions[session_id] = InvoiceDraft()
        return self.sessions[session_id]

    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

class InvoiceStorage:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def _load_invoices(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    return json.load(f)
            except: pass
        return []

    def save_invoice(self, draft: InvoiceDraft):
        invoices = self._load_invoices()
        invoices.append(draft.to_dict())
        with open(self.storage_path, "w") as f:
            json.dump(invoices, f, indent=4)
        return draft.invoice_id

class InvoiceParser:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model = genai.GenerativeModel(model_name)

    def update_draft(self, draft: InvoiceDraft, text: str) -> InvoiceDraft:
        current_data = draft.to_dict()
        prompt = f"""
        You are an AI assistant that extracts invoice details. 
        Update the current invoice data with new information from the user's text.
        
        Current Data: {json.dumps(current_data)}
        User Text: "{text}"
        
        RULES:
        1. If user provides a name, update 'customer_name'.
        2. If user provides an email, update 'customer_email'.
        3. If items are mentioned, ADD them to the existing items list or update them.
        4. If GST/Tax is mentioned, update 'customer_gst' or 'tax_percent'.
        5. If a discount/offer/coupon is mentioned, update 'discount_code' or 'discount'.
        6. Return ONLY the complete updated JSON object matching the structure below.
        
        JSON Structure:
        {{
            "invoice_number": string,
            "customer_name": string,
            "customer_email": string,
            "customer_gst": string,
            "currency": string,
            "tax_percent": number,
            "shipping_fee": number,
            "discount": number,
            "discount_code": string,
            "items": [
                {{"name": string, "quantity": number, "unit_price": number}}
            ]
        }}
        """
        try:
            response = self.model.generate_content(prompt)
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                if 'items' in data:
                    draft.items = [InvoiceItem(**item) for item in data['items']]
                draft.invoice_number = data.get('invoice_number', draft.invoice_number)
                draft.customer_name = data.get('customer_name', draft.customer_name)
                draft.customer_email = data.get('customer_email', draft.customer_email)
                draft.customer_gst = data.get('customer_gst', draft.customer_gst)
                draft.tax_percent = data.get('tax_percent', draft.tax_percent)
                draft.shipping_fee = data.get('shipping_fee', draft.shipping_fee)
                draft.discount = data.get('discount', draft.discount)
                draft.discount_code = data.get('discount_code', draft.discount_code)
                
                if not draft.invoice_date:
                    draft.invoice_date = datetime.now().strftime("%Y-%m-%d")
                if not draft.due_date:
                    draft.due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        except Exception as e:
            print(f"Error parsing: {e}")
        return draft

class InvoiceEngine:
    REQUIRED_FIELDS = ["customer_name", "customer_email"]

    def validate(self, draft: InvoiceDraft) -> List[str]:
        missing = []
        if not draft.customer_name: missing.append("customer_name")
        if not draft.customer_email: missing.append("customer_email")
        if not draft.items: missing.append("items")
        return missing

    def suggestions(self, draft: InvoiceDraft) -> List[str]:
        tips = []
        if not draft.customer_name: tips.append("What is the customer's name?")
        if not draft.customer_email: tips.append("Could you provide their email address?")
        if not draft.customer_gst: tips.append("Do you have a GST number to include? (Optional but recommended)")
        if not draft.discount_code: tips.append("Do you have any discount codes or offers to apply?")
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
            lines.append(f"• {item.name} — {item.quantity:g} × {item.unit_price:.2f} = {item.line_total:.2f}")
        
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
        self.parser = InvoiceParser()
        self.engine = InvoiceEngine()
        self.sessions = SessionManager()
        storage_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "invoices.json")
        self.storage = InvoiceStorage(storage_path)

    def process_message(self, user_message: str, session_id: str = "default") -> Dict[str, Any]:
        msg = user_message.lower()
        draft = self.sessions.get_draft(session_id)

        # Detect intent to start or continue an invoice
        is_invoice_talk = any(kw in msg for kw in ["invoice", "bill", "checkout", "to raju", "@", "gmail", "com", "gst"])
        
        if is_invoice_talk or draft.items:
            draft = self.parser.update_draft(draft, user_message)
            missing = self.engine.validate(draft)

            if missing:
                suggestions = self.engine.suggestions(draft)
                text = (
                    "I've updated your draft, but I'm still missing some details:\n\n"
                    + "\n".join(f"• {tip}" for tip in suggestions)
                    + "\n\nJust type them in and I'll update the bill!"
                )
                return {"text": text, "type": "warning"}

            # If all required fields are here, and it's the first time we have them all, or they say "confirm"
            if not missing:
                # auto-generate or ask to confirm? 
                # The user wants "python script should be run to create an invoice for that"
                # so we generate and save.
                invoice_id = self.storage.save_invoice(draft)
                text = "### 🚀 Invoice Generated Successfully!\n\n" + self.engine.render_invoice(draft)
                self.sessions.clear_session(session_id) # Reset for next one
                return {"text": text, "type": "invoice", "saved_invoice_id": invoice_id}

        # Fallback to general assistant
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(f"User: {user_message}. Act as UrbanStyle Shopping Assistant. If they want to bill or checkout, guide them.")
            return {"text": response.text, "type": "info"}
        except:
            return {"text": "How can I help you shop today?", "type": "info"}

BizzHubChatbot = InvoiceAssistantChatbot
