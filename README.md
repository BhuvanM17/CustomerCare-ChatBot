# AI-Powered E-Commerce Invoice Assistant

An intelligent invoice assistant that turns user input into structured invoices, validates missing fields, and suggests additions before final generation.

## 📁 Project Structure

```
CustomerCare-ChatBot/
├── api/                # Vercel serverless API entrypoint
│   └── app.py
├── backend/            # Local Flask backend + core logic
│   ├── core/
│   │   └── agent.py    # Parser, validation, generation engine
│   ├── app.py
│   └── requirements.txt
├── frontend/           # Web chat interface
│   ├── index.html
│   ├── style.css
│   └── script.js
├── vercel.json         # Vercel routing/build config
└── README.md
```

## 🚀 Run Locally

### 1) Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Backend runs at `http://localhost:5000`.

### 2) Frontend

Open `frontend/index.html` in a browser (or serve it using any static server).

## ☁️ Deploy to Vercel

1. Push this repo to GitHub.
2. Import the project in Vercel.
3. Vercel will auto-detect `vercel.json` and deploy:
   - Static frontend from `frontend/`
   - Python API from `api/app.py` (`/api/chat`, `/api/health`)
4. After deploy, open your Vercel URL and chat with the assistant.

> Frontend uses `http://localhost:5000/chat` in local mode and automatically switches to `/api/chat` in production.

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
