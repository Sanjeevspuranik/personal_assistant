# 🚀 Personal Assistant  
An AI-powered, tool-using personal assistant built to automate daily tasks, perform intelligent searches, generate files, evaluate its own work, and boost productivity — powered by **LangGraph**, **LangChain**, **OpenAI GPT-4o mini**, and **Playwright**.

---

## 🌟 Features

### 🔧 Core Functionality
- 🌐 Web Searching (via browser automation)
- 📧 Email Sending
- 📁 File System Access (read/write/modify)
- 📖 Wikipedia Integration
- 🧮 Python REPL Execution

### 🤖 Intelligent Workflow
- Multi-step **worker → tools → evaluator** cycle  
- Self-evaluation of responses  
- Success-criteria driven task completion  
- Built-in memory using **MemorySaver**

### 🖥️ Automation Tools
- Playwright browser control  
- File creation / markdown generation  
- Push notifications  
- Structured outputs & validation  

## Prerequisites

- Python 3.12 or higher  
- `pip` for installing dependencies  

## Installation

```bash
git clone https://github.com/Sanjeevspuranik/personal_assistant.git
cd personal_assistant
pip install -r requirements.txt
```
## Running the application
```bash
uv run app.py
```

## structure
```bash
personal_assistant/
│
├── app.py                 # main entry point
├── sidekick.py            # core logic / assistant module
├── sidekick_tools.py      # auxiliary tools / helper functions
├── requirements.txt       # Python dependencies
└── .gitignore             # gitignore file
```

## Usage

After running app.py, the assistant will start and allow you to use features such as web search, Wikipedia lookup, file operations, and sending emails.

## Contributing

Contributions are welcome!

- Open issues for bugs or feature requests.

- ull requests should follow the existing code style.

## 📸 Demo Screenshots

### **Execution Summary View**

<img src="sample_run/push_notification.jpg" alt="Push notification" width="400"/>

### **Generated Markdown Output Example**

[Results](sample_run/day_out_bengaluru.md)

---

## 🎥 Sample Run (Video)

[Live run](sample_run/Live_run.mp4)

## 🧑‍💻 Author

Built by [Sanjeev Spuranik](https://github.com/Sanjeevspuranik) — passionate about modular AI systems, semantic search, and educational tooling.
