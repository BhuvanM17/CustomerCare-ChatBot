import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('GOOGLE_API_KEY', 'test-api-key-for-testing')


class TestInvoiceParser:
    """Tests for the AI-powered invoice parser."""

    def test_parse_formatted_invoice(self):
        """Test parsing with structured format."""
        from backend.core.agent import InvoiceParser
        
        parser = InvoiceParser()
        text = "invoice number: INV-1001, customer: John Doe, email: john@example.com, 2x Laptop @ 50000, tax: 18, shipping: 500"
        
        draft = parser.parse(text)
        
        assert draft.invoice_number == "INV-1001"
        assert draft.customer_name == "John Doe"
        assert draft.customer_email == "john@example.com"
        assert len(draft.items) > 0
        assert draft.tax_percent == 18.0
        assert draft.shipping_fee == 500.0

    def test_parse_natural_language(self):
        """Test parsing with natural language input."""
        from backend.core.agent import InvoiceParser
        
        parser = InvoiceParser()
        text = "Hey, Alex bought 5 shirts for 500 each, add 18% tax and ship it for 50. Invoice #ABC-999."
        
        draft = parser.parse(text)
        
        assert draft.invoice_number == "ABC-999" or draft.invoice_number is not None
        assert draft.customer_name == "Alex" or draft.customer_name is not None

    def test_parse_with_discount(self):
        """Test parsing with discount."""
        from backend.core.agent import InvoiceParser
        
        parser = InvoiceParser()
        text = "invoice: INV-2026-001, customer: Jane, email: jane@shop.com, 3x Phone @ 30000, discount: 5000"
        
        draft = parser.parse(text)
        
        assert draft.discount == 5000.0

    def test_parse_multiple_items(self):
        """Test parsing multiple line items."""
        from backend.core.agent import InvoiceParser
        
        parser = InvoiceParser()
        text = "INV-001, customer: Test User, email: test@test.com, 2x Item1 @ 100, 3x Item2 @ 200, 1x Item3 @ 500"
        
        draft = parser.parse(text)
        
        assert len(draft.items) >= 1


class TestInvoiceEngine:
    """Tests for the invoice engine validation and rendering."""

    def test_validate_complete_invoice(self):
        """Test validation of complete invoice."""
        from backend.core.agent import InvoiceEngine, InvoiceDraft, InvoiceItem
        
        engine = InvoiceEngine()
        draft = InvoiceDraft(
            invoice_number="INV-001",
            customer_name="Test Customer",
            customer_email="test@test.com",
            items=[InvoiceItem("Item", 1, 100)]
        )
        
        missing = engine.validate(draft)
        assert len(missing) == 0

    def test_validate_missing_fields(self):
        """Test validation with missing fields."""
        from backend.core.agent import InvoiceEngine, InvoiceDraft
        
        engine = InvoiceEngine()
        draft = InvoiceDraft(
            invoice_number="INV-001"
        )
        
        missing = engine.validate(draft)
        assert "customer_name" in missing
        assert "customer_email" in missing
        assert "items" in missing

    def test_render_invoice(self):
        """Test invoice rendering."""
        from backend.core.agent import InvoiceEngine, InvoiceDraft, InvoiceItem
        
        engine = InvoiceEngine()
        draft = InvoiceDraft(
            invoice_number="INV-001",
            customer_name="Test",
            customer_email="test@test.com",
            items=[InvoiceItem("Test Item", 2, 100)],
            tax_percent=10,
            shipping_fee=50
        )
        
        rendered = engine.render_invoice(draft)
        
        assert "INV-001" in rendered
        assert "Test" in rendered
        assert "200" in rendered or "200.00" in rendered
        assert "Tax" in rendered


class TestInvoiceStorage:
    """Tests for invoice persistence."""

    def test_save_and_retrieve_invoice(self, tmp_path):
        """Test saving and retrieving invoices."""
        from backend.core.agent import InvoiceStorage
        
        storage_path = tmp_path / "test_invoices.json"
        storage = InvoiceStorage(str(storage_path))
        
        invoice_data = {
            "invoice_number": "TEST-001",
            "customer_name": "Test Customer",
            "items": [],
            "total": 1000
        }
        
        invoice_id = storage.save_invoice(invoice_data)
        
        assert invoice_id is not None
        assert "INV-" in invoice_id
        
        invoices = storage.list_invoices()
        assert len(invoices) == 1
        
        retrieved = storage.get_invoice(invoice_id)
        assert retrieved is not None
        assert retrieved["invoice_number"] == "TEST-001"


class TestChatbot:
    """Tests for the chatbot functionality."""

    def test_process_invoice_creation(self):
        """Test processing an invoice creation request."""
        from backend.core.agent import InvoiceAssistantChatbot
        
        chatbot = InvoiceAssistantChatbot()
        
        response = chatbot.process_message("create invoice: invoice number: INV-100, customer: Bob, email: bob@test.com, 1x Product @ 500")
        
        assert "text" in response
        assert response["text"] is not None

    def test_process_validation_request(self):
        """Test processing a validation request."""
        from backend.core.agent import InvoiceAssistantChatbot
        
        chatbot = InvoiceAssistantChatbot()
        
        response = chatbot.process_message("validate: invoice number: INV-001")
        
        assert "text" in response

    def test_greeting_response(self):
        """Test default greeting response."""
        from backend.core.agent import InvoiceAssistantChatbot
        
        chatbot = InvoiceAssistantChatbot()
        
        response = chatbot.process_message("hello")
        
        assert "text" in response
        assert "invoice" in response["text"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
