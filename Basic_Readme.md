# 📄 Agentic PDF Translator

A multi-agent AI-powered document translation system built with **LangChain** and **Google Gemini**. It uses an orchestrated pipeline of specialized agents to translate PDF documents across languages with built-in quality assurance.

---

## ✨ Features

- **Multi-Agent Architecture** — Specialized agents handle intake, planning, execution, QA, judging, and delivery.
- **LLM-Powered Translation** — Uses Google Gemini for high-quality, context-aware translations.
- **Quality Assurance Loop** — Automated QA agent reviews translations; a Judge agent arbitrates retries.
- **Streamlit UI** — Interactive web interface for uploading documents and monitoring translation progress.
- **CLI Support** — Run translations directly from the command line with flexible options.
- **Configurable** — Supports multiple source/target languages and document types (legal, medical, etc.).

---

## 🏗️ Project Structure

```
Agentic pdf translator/
├── app/
│   └── streamlit_app.py        # Streamlit web interface
├── src/
│   ├── main.py                 # CLI entry point
│   ├── agents/                 # Agent implementations
│   │   ├── base_agent.py       # Base agent class
│   │   ├── intake_agent.py     # Document intake & validation
│   │   ├── planner_agent.py    # Translation planning
│   │   ├── execution_agent.py  # Core translation execution
│   │   ├── qa_agent.py         # Quality assurance checks
│   │   ├── judge_agent.py      # QA arbitration & retry decisions
│   │   ├── delivery_agent.py   # Final output packaging
│   │   └── master_agent.py     # Top-level agent coordinator
│   ├── config/
│   │   └── settings.py         # Application settings (via Pydantic)
│   ├── models/
│   │   ├── workflow_state.py   # Workflow state definitions
│   │   └── outputs.py          # Output data models
│   ├── workflow/
│   │   ├── orchestrator.py     # Workflow orchestration engine
│   │   ├── routing.py          # Agent routing logic
│   │   └── state_manager.py    # State management
│   └── utils/                  # Utility functions
├── tests/                      # Unit & integration tests
├── examples/                   # Sample input documents
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
└── pytest.ini                  # Pytest configuration
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- A **Google Gemini API key** ([Get one here](https://aistudio.google.com/apikey))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/aniket21715/Agentic_Pdf_Translator
   cd "Agentic pdf translator"
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   # source venv/bin/activate   # macOS/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   copy .env.example .env       # Windows
   # cp .env.example .env       # macOS/Linux
   ```
   Open `.env` and set your API key:
   ```env
   GOOGLE_API_KEY=your_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```

---

## 💻 Usage

### Web Interface (Streamlit)

```bash
streamlit run app/streamlit_app.py
```

This opens an interactive UI where you can upload documents, select languages, and monitor translation progress.

### Command Line

```bash
python -m src.main --input-file examples/sample_document.txt \
                   --source-language en \
                   --target-language es \
                   --document-type legal \
                   --use-real-llm
```

**CLI Options:**

| Flag                   | Description                              | Default                  |
|------------------------|------------------------------------------|--------------------------|
| `--input-file`         | Path to the input document               | `examples/sample_document.txt` |
| `--source-language`    | Source language code (e.g., `en`)         | From `.env`              |
| `--target-language`    | Target language code (e.g., `es`)        | From `.env`              |
| `--document-type`      | Document type (`legal`, `medical`, etc.) | From `.env`              |
| `--page-count`         | Number of pages to process               | `3`                      |
| `--use-real-llm`       | Use the real Gemini LLM (vs. mock)       | `false`                  |
| `--require-approval`   | Require manual approval at each step     | `false`                  |
| `--parallel`           | Enable parallel page translation         | `false`                  |
| `--output-file`        | Path for the output JSON file            | `examples/example_outputs/latest_output.json` |

---

## ⚙️ Configuration

All settings can be configured via the `.env` file:

| Variable                     | Description                         | Default        |
|------------------------------|-------------------------------------|----------------|
| `GOOGLE_API_KEY`             | Your Google Gemini API key          | —              |
| `GEMINI_MODEL`               | Gemini model to use                 | `gemini-2.5-flash` |
| `USE_REAL_LLM`               | Enable real LLM calls               | `false`        |
| `DEFAULT_SOURCE_LANGUAGE`    | Default source language             | `en`           |
| `DEFAULT_TARGET_LANGUAGE`    | Default target language             | `es`           |
| `DEFAULT_DOCUMENT_TYPE`      | Default document type               | `legal`        |
| `DEFAULT_MAX_RETRIES`        | Max QA retry attempts               | `1`            |
| `SLA_SECONDS`                | SLA timeout in seconds              | `120`          |

---

## 🧪 Running Tests

```bash
pytest
```

---

## 🛠️ Tech Stack

| Technology            | Purpose                          |
|-----------------------|----------------------------------|
| **LangChain**         | Agent framework & LLM chaining   |
| **Google Gemini**     | Large Language Model provider    |
| **Pydantic**          | Data validation & settings       |
| **Streamlit**         | Web UI framework                 |
| **PyPDF / FPDF2**     | PDF reading & generation         |
| **Loguru**            | Logging                          |
| **Pytest**            | Testing framework                |

---

