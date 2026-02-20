# AI-Powered E-Commerce Invoice Assistant

An intelligent invoice assistant that turns user input into structured invoices, validates missing fields, and suggests additions before final generation.

## 📁 Project Structure

```
CustomerCare-ChatBot/
├── backend/            # Python Flask Backend
│   ├── core/           # Invoice assistant logic
│   │   └── agent.py    # Parser, validation, generation engine
│   ├── app.py          # API server
│   └── requirements.txt
├── frontend/           # Web chat interface
│   ├── index.html
│   ├── style.css
│   └── script.js
└── README.md
```

## 🚀 Getting Started

### 1) Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Backend runs at `http://localhost:5000`.

### 2) Frontend

Open `frontend/index.html` in a browser (or use a local static server).

## 🌟 Features

- **Invoice generation from plain text** (e.g., `2x Sneakers @ 2499`).
- **Intelligent validation** for required fields:
  - invoice number
  - customer name
  - customer email
  - at least one line item
- **AI-style suggestions** for missing details.
- **Dynamic totals** with tax, shipping, and discount.

## 💼 Projects

- Developed an **AI-driven invoicing system** that generates invoices from user input using LLM-style parsing logic.
- Implemented **intelligent validation** that detects missing fields and suggests additions via AI prompts.
- Built backend APIs for data processing and dynamic invoice generation, improving accuracy and user efficiency.

## 🧪 Sample Prompt

```text
Generate invoice: invoice number: INV-1001, customer: Alex, email: alex@shop.com, 2x Sneakers @ 2499, tax: 18, shipping: 99
```
