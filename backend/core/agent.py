import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional


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
    invoice_number: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: str = "INR"
    tax_percent: float = 0.0
    shipping_fee: float = 0.0
    discount: float = 0.0
    items: List[InvoiceItem] = field(default_factory=list)


class InvoiceParser:
    """Extract invoice fields from natural language + lightweight templates."""

    FIELD_PATTERNS = {
        "invoice_number": r"(?:invoice\s*(?:number|#)\s*[:=-]\s*)([\w\-/]+)",
        "customer_name": r"(?:customer|client|buyer)\s*(?:name)?\s*[:=-]\s*([^,;\n]+)",
        "customer_email": r"(?:email|mail)\s*[:=-]\s*([\w\.-]+@[\w\.-]+\.\w+)",
        "invoice_date": r"(?:invoice\s*date|date)\s*[:=-]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",
        "due_date": r"(?:due\s*date|due)\s*[:=-]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",
        "currency": r"(?:currency)\s*[:=-]\s*([A-Za-z]{3})",
        "tax_percent": r"(?:tax|gst|vat)\s*[:=-]?\s*([0-9]+(?:\.[0-9]+)?)%?",
        "shipping_fee": r"(?:shipping|delivery)\s*(?:fee|charge|cost)?\s*[:=-]?\s*([0-9]+(?:\.[0-9]+)?)",
        "discount": r"(?:discount)\s*[:=-]?\s*([0-9]+(?:\.[0-9]+)?)",
    }

    ITEM_PATTERN = re.compile(
        r"(?P<qty>[0-9]+(?:\.[0-9]+)?)\s*x\s*(?P<name>[A-Za-z0-9\-\s]+?)\s*@\s*(?P<price>[0-9]+(?:\.[0-9]+)?)",
        re.IGNORECASE,
    )

    def parse(self, text: str) -> InvoiceDraft:
        draft = InvoiceDraft()

        for field_name, pattern in self.FIELD_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            value = match.group(1).strip()
            if field_name in {"tax_percent", "shipping_fee", "discount"}:
                setattr(draft, field_name, float(value))
            elif field_name == "currency":
                draft.currency = value.upper()
            else:
                setattr(draft, field_name, value)

        for item_match in self.ITEM_PATTERN.finditer(text):
            draft.items.append(
                InvoiceItem(
                    name=item_match.group("name").strip(),
                    quantity=float(item_match.group("qty")),
                    unit_price=float(item_match.group("price")),
                )
            )

        if not draft.invoice_date:
            draft.invoice_date = datetime.now().strftime("%Y-%m-%d")
        if not draft.due_date:
            draft.due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        return draft


class InvoiceEngine:
    REQUIRED_FIELDS = ["invoice_number", "customer_name", "customer_email"]

    def validate(self, draft: InvoiceDraft) -> List[str]:
        missing = []
        for field in self.REQUIRED_FIELDS:
            if not getattr(draft, field):
                missing.append(field)

        if not draft.items:
            missing.append("items")

        return missing

    def suggestions(self, missing_fields: List[str]) -> List[str]:
        hints = {
            "invoice_number": "Add `invoice number: INV-2026-001`.",
            "customer_name": "Add `customer: Jane Doe`.",
            "customer_email": "Add `email: jane@store.com`.",
            "items": "Add line items in `qty x item @ price` format (example: `2x T-shirt @ 799`).",
        }
        return [hints[item] for item in missing_fields if item in hints]

    def render_invoice(self, draft: InvoiceDraft) -> str:
        subtotal = round(sum(item.line_total for item in draft.items), 2)
        tax = round(subtotal * (draft.tax_percent / 100), 2)
        total = round(subtotal + tax + draft.shipping_fee - draft.discount, 2)

        lines = [
            f"🧾 **Invoice {draft.invoice_number}**",
            f"**Customer:** {draft.customer_name}",
            f"**Email:** {draft.customer_email}",
            f"**Invoice Date:** {draft.invoice_date}",
            f"**Due Date:** {draft.due_date}",
            "",
            "**Line Items**",
        ]

        for item in draft.items:
            lines.append(
                f"• {item.name} — {item.quantity:g} × {item.unit_price:.2f} = {item.line_total:.2f} {draft.currency}"
            )

        lines.extend(
            [
                "",
                f"**Subtotal:** {subtotal:.2f} {draft.currency}",
                f"**Tax ({draft.tax_percent:g}%):** {tax:.2f} {draft.currency}",
                f"**Shipping:** {draft.shipping_fee:.2f} {draft.currency}",
                f"**Discount:** -{draft.discount:.2f} {draft.currency}",
                f"✅ **Grand Total:** {total:.2f} {draft.currency}",
            ]
        )

        return "\n".join(lines)


class InvoiceAssistantChatbot:
    """AI-Powered E-Commerce Invoice Assistant."""

    def __init__(self):
        self.parser = InvoiceParser()
        self.engine = InvoiceEngine()
        print("🤖 AI-Powered E-Commerce Invoice Assistant initialized")

    def process_message(self, user_message: str) -> str:
        message = user_message.lower()

        if any(keyword in message for keyword in ["validate", "check fields", "missing fields"]):
            draft = self.parser.parse(user_message)
            missing = self.engine.validate(draft)
            if not missing:
                return "✅ Your invoice input looks complete and ready for generation."
            return (
                "⚠️ Validation result: missing required details -> "
                + ", ".join(missing)
                + "\n"
                + "\n".join(f"• {tip}" for tip in self.engine.suggestions(missing))
            )

        if any(keyword in message for keyword in ["create invoice", "generate invoice", "invoice"]):
            draft = self.parser.parse(user_message)
            missing = self.engine.validate(draft)

            if missing:
                suggestions = "\n".join(f"• {tip}" for tip in self.engine.suggestions(missing))
                return (
                    "I found missing fields in your invoice request:\n"
                    f"• {', '.join(missing)}\n\n"
                    "Suggested additions:\n"
                    f"{suggestions}"
                )

            return self.engine.render_invoice(draft)

        return (
            "Hi! I'm your **AI-Powered E-Commerce Invoice Assistant**.\n\n"
            "I can help you:\n"
            "• Generate invoices from plain-text input\n"
            "• Validate missing fields\n"
            "• Suggest what to add before finalizing\n\n"
            "Try:\n"
            "`Generate invoice: invoice number: INV-1001, customer: Alex, email: alex@shop.com, 2x Sneakers @ 2499, tax: 18, shipping: 99`"
        )


# Backward compatibility for existing imports
BizzHubChatbot = InvoiceAssistantChatbot
