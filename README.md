# 💰 AI-Powered Personal Finance Assistant

![React](https://img.shields.io/badge/Frontend-React%20+%20Vite-61DAFB?logo=react)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)
![LangChain](https://img.shields.io/badge/AI-LangChain-blue?logo=OpenAI)
![Google Cloud](https://img.shields.io/badge/Database-Google%20Cloud%20SQL-4285F4?logo=googlecloud)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📖 Overview

![image](Images/Dashboard_Overview.jpg)


Managing personal finances is often overwhelming, with data scattered across accounts, platforms, and services.  
This project is an **AI-powered Personal Finance Assistant** built with **React + Vite (Frontend)** and **FastAPI (Backend)**, designed to centralize, analyze, and provide **AI-driven insights** into your finances.

✨ Key highlights:
- **24×7 AI Assistant**: Chat anytime to ask financial questions.
- **Quick AI Chat**: Get instant, context-aware answers about your data.
- **Interactive Graphs**: Visualize assets, liabilities, investments, and savings with bar, line, histogram, and pie charts.
- **Transaction History**: View past expenses and income in a clean dashboard.
- **User Control**: Grant or revoke access to specific data categories for privacy.

---

## 🚀 Features

- 🤖 **AI-Powered Chat**: Ask *“Can I afford a vacation next month?”* or *“Why did my expenses increase last quarter?”*.  
- 📊 **Dynamic Charts**: Visualize investments, savings, and transactions in multiple formats.  
- 🔄 **Past Transaction History**: Track all your income/expenses over time.  
- 🔒 **User Privacy Control**: Grant or revoke access to assets, liabilities, investments, etc.  
- ☁️ **Scalable Backend**: FastAPI with serverless design + Google Cloud SQL.  
- 🔗 **LangChain AI Core**: Sequential workflow agent for personalized financial insights.  

---

## 🏗️ Tech Stack

- **Frontend:** React + Vite, Chart.js  
- **Backend:** Python FastAPI (3-Layer Architecture → API Layer, Data Management, AI Core)  
- **AI Core:** LangChain (Agentic Workflows)  
- **Database:** Google Cloud SQL + SQLAlchemy ORM  
- **Hosting:** GCP (Serverless Backend for scalability)  

---

## ⚙️ Setup Instructions

### 1️⃣ Clone Repository
```bash
git clone https://github.com/your-username/finance-ai-assistant.git
cd finance-ai-assistant
```

### 2️⃣ Backend Setup (FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate   # (On Windows: venv\Scripts\activate)
pip install -r requirements.txt
```

Create a `.env` file inside the backend folder with the following variables:

```ini
GOOGLE_API_KEY=your_google_api_key
DB_USER=your_db_user
DB_PASS=your_db_password
DB_NAME=your_db_name
PUBLIC_IP=your_db_public_ip
DB_PORT=your_db_port
```

Run the FastAPI server:
```bash
uvicorn main:app --reload
```

---

### 3️⃣ Frontend Setup (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

Frontend will start on **http://localhost:5173/**  

---
![alt text](<D:\LJ_Hackovate\WhatsApp Image 2025-09-14 at 10.54.37_754b400a.jpg>)
## ☁️ Google Cloud SQL Setup

1. Create a **Google Cloud SQL instance** (PostgreSQL/MySQL).  
2. Note the **DB_USER, DB_PASS, DB_NAME, PUBLIC_IP, DB_PORT**.  
3. Whitelist your public IP for connections.  
4. Use these credentials in your `.env` file.  

---

## 🔑 Things to Remember

### React + Vite
- Always run `npm install` after cloning.  
- Use `npm run dev` for local development.  
- Environment variables for frontend go into `.env` with `VITE_` prefix (e.g., `VITE_API_URL=http://localhost:8000`).  

### FastAPI
- Use **.env file** for all secrets (DB, API keys).  
- Run server with `uvicorn main:app --reload`.  
- Test endpoints at `http://localhost:8000/docs`.  

---

## 📈 System Architecture

```
Frontend (React + Vite + Chart.js)
        ⬇
Backend (FastAPI)
    ├── API Layer (Request handling, Permissions)
    ├── Data Management Layer (SQLAlchemy + Cloud SQL)
    └── AI Core (LangChain Workflows)
        ⬇
Final JSON Response → Rendered in React (Charts + AI Chat)
```

---

## 📸 Screenshots (Optional)
_Add screenshots of your dashboard, AI chat, and graphs here._

---
![alt text](<D:\LJ_Hackovate\WhatsApp Image 2025-09-14 at 10.55.25_15a6b707.jpg>)
## 🤝 Contributors
- 👨‍💻 Your Name  
- 👩‍💻 Team Member  

---

## 📜 License
This project is licensed under the MIT License.  

---

## 🌟 Final Note
This project demonstrates how AI can **“Speak to Your Money”** by combining structured data, interactive visualization, and AI-driven insights to empower better financial decision-making.  


