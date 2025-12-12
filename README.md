# 🤖 Gemini Operator: Autonomous Web Agent

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![GenAI](https://img.shields.io/badge/Powered%20by-Gemini%20Pro-orange.svg)](https://deepmind.google/technologies/gemini/)
[![Selenium](https://img.shields.io/badge/Automation-Selenium-green.svg)](https://www.selenium.dev/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)]()

**Gemini Operator** is an intelligent, context-aware autonomous agent designed to navigate the web, interpret user intent, and perform complex tasks without brittle, hard-coded scripts.

Unlike traditional web scrapers, this system utilizes **LLM-driven reasoning** to plan actions dynamically and features a **Self-Healing Mechanism** that automatically updates its knowledge base when UI structures change.

---

## 🚀 Key Features (核心亮點)

### 🧠 1. Cognitive Reasoning Engine (ReAct Pattern)
- Uses **Google Gemini 2.5 Pro** as the brain to analyze the current DOM context.
- Decomposes high-level user instructions (e.g., *"Find the cheapest iPhone on PChome"*) into executable steps (`Maps`, `search`, `click`).
- Implements a **feedback loop** to verify action success before proceeding.

### 🛡️ 2. Self-Healing Infrastructure
- **Dynamic Selector Recovery:** When a CSS selector fails (due to website updates), the agent captures the HTML snapshot.
- **Visual Analysis:** The "Teacher" model analyzes the page structure to identify the new stable selector for the intended element.
- **Knowledge Base Update:** Automatically patches `knowledge_base.json` with the new selector, ensuring the next run succeeds.

### 📚 3. Semantic Knowledge Base
- Maintains a thread-safe JSON database mapping **Human Intents** (e.g., "Search Button") to **Robust CSS Selectors**.
- Supports continuous learning: The more it browses, the smarter and more robust it becomes.

---

## 🏗️ Architecture (系統架構)

The system follows a modular micro-architecture separating the **Brain (Agent)**, the **Eyes/Hands (Browser Tools)**, and the **Memory (Knowledge Base)**.

mermaid
graph TD
    User[User Instruction] -->|WebSocket| Server[Flask Server]
    Server --> Agent[Agent Core (Orchestrator)]
    
    subgraph "Reasoning Loop"
        Agent -->|Context + Goal| LLM[Gemini Pro Model]
        LLM -->|Execution Plan| Agent
    end
    
    subgraph "Execution Layer"
        Agent -->|Action| Browser[Browser Tools (Selenium)]
        Browser -->|Interact| Web[Target Website]
        Web -->|DOM State| Browser
    end
    
    subgraph "Self-Healing Layer"
        Browser -->|Error/Failure| KB_Builder[Knowledge Builder]
        KB_Builder -->|Analyze Snapshot| LLM
        LLM -->|New Selector| KB[Knowledge Base (JSON)]
        KB -->|Retry Strategy| Agent
    end


🛠️ Tech Stack
Core: Python 3.12

LLM Integration: Google Generative AI SDK (Gemini 1.5/2.5 Pro)

Web Automation: Selenium WebDriver (Chrome)

Backend: Flask, Flask-SocketIO (Async Event Handling)

Concurrency: Threading (Thread-safe file I/O operations)

⚡ Quick Start
Prerequisites
Python 3.10+

Google Cloud API Key (with Gemini access)

Chrome Browser installed

Installation
Clone the repository

Bash

git clone [https://github.com/your-username/gemini-operator.git](https://github.com/your-username/gemini-operator.git)
cd gemini-operator
Install dependencies

Bash

pip install -r requirements.txt
Configure Environment Create a .env file in the root directory:

程式碼片段

GOOGLE_API_KEY=your_actual_api_key_here
Run the Application

Bash

python app.py
Visit http://localhost:5000 to interact with the agent.

📂 Project Structure
Plaintext

gemini-operator/
├── agent/
│   ├── agent_core.py       # Main Logic: Planning & Execution Loop
│   ├── browser_tools.py    # Tooling: Selenium Wrappers & Snapshot
│   ├── knowledge_builder.py# Core Feature: AI Analysis & Self-Healing
│   └── knowledge_base.py   # Thread-safe Database Management
├── static/                 # Frontend Assets
├── templates/              # UI Templates
├── app.py                  # Entry Point (Flask + SocketIO)
└── knowledge_base.json     # The "Long-term Memory" of the agent
🔮 Future Roadmap
[ ] Dockerization: Containerize the application for cloud deployment (AWS/GCP).

[ ] Headless Mode: Optimize for server-side execution without UI rendering.

[ ] Vector Database: Migrate knowledge_base.json to a vector store (e.g., Pinecone/ChromaDB) for semantic retrieval.
