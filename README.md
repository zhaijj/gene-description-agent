# 🧬 Maize Gene Description Agent

A "Pro" Streamlit agent that generates deep functional summaries for Maize genes using Google Gemini.

## ✨ Features

- **🤖 AI-Powered Analysis**: Generates comprehensive descriptions using Gemini 2.5/3 Pro models.
- **📊 Traffic Analytics**: Tracks visitor locations and displays live traffic stats and map.
- **👍 Interactive Feedback**: Rate responses (Thumbs Up/Down) and leave general comments.
- **📥 Download Reports**: Save generated descriptions as Markdown files.
- **🎨 Maize Theme**: Custom Green & Gold UI with a polished sidebar and animated DNA loader.

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- A Google Gemini API Key

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/zhaijj/gene-description-agent.git
    cd gene-description-agent
    ```

2.  **Create a virtual environment**:
    ```bash
    python3 -m venv venv_2
    source venv_2/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### Usage

1.  **Run the application**:
    ```bash
    streamlit run app.py
    ```

2.  **Enter your API Key**: Using the sidebar.
3.  **Search**: Enter a gene ID (e.g., `Zm00001eb126570`) or click an example button.
4.  **Explore**: View the description, check the traffic map, or download the report.

## 📂 Data Storage

- `analytics.csv`: Visitor traffic logs.
- `feedback.csv`: User ratings for gene descriptions.
- `comments.csv`: General user comments logged from the sidebar.

> **Note**: This agent works best with *Zea mays* gene models (e.g., B73 RefGen_v5).