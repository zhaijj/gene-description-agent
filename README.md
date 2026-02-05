# 🧬 Plant Gene Description Agent

A "Pro" Streamlit agent that generates deep functional summaries for Plant genes (Maize, Rice, Arabidopsis, etc.) using Google Gemini.

🔗 **[Live Demo](https://zhaijj-gene-description-agent-app-temssq.streamlit.app)**

## ✨ Features

- **🌱 Multi-Species Support**: Works with Maize, Rice, Arabidopsis, Sorghum, and allows custom species input (e.g., *Solanum lycopersicum*).
- **🤖 AI-Powered Analysis**: Generates comprehensive descriptions using Gemini 2.5/3 Pro models.
- **📊 Traffic Analytics**: Tracks visitor locations and displays live traffic stats and map.
- **👍 Interactive Feedback**: Rate responses (Thumbs Up/Down) and leave general comments.
- **📥 Download Reports**: Save generated descriptions as Markdown files.
- **🎨 Modern UI**: Clean, dynamic interface with species-specific examples and validation.

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

2.  **Configuration**:
    - Enter your **Gemini API Key**.
    - Enter your **NCBI Email** (Required for Entrez API).
    - *Optionally save the email to local .env*.
3.  **Search**: 
    - Select a **Species** from the sidebar (e.g., Maize, Rice, Arabidopsis).
    - Enter a gene ID (e.g., `AT5G10140` for Arabidopsis) or click one of the **dynamic example buttons**.
4.  **Explore**: View the description, check the traffic map, or download the report.

## 📂 Data Storage

- `analytics.csv`: Visitor traffic logs.
- `feedback.csv`: User ratings for gene descriptions.
- `comments.csv`: General user comments logged from the sidebar.

> **Note**: This agent leverages g:Profiler for ortholog conversion. While verified for Maize, Rice, and Arabidopsis, other species support depends on g:Profiler's database coverage.