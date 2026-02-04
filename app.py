import traceback
import streamlit as st
import importlib
import src.agent
importlib.reload(src.agent)
from src.agent import GeneDescriptionAgent

# Initialize the agent
def get_agent(api_key, model_name):
    try:
        return GeneDescriptionAgent(api_key=str(api_key), model_name=model_name)
    except Exception as e:
        st.error(f"Failed to initialize Agent: {e}")
        st.code(traceback.format_exc())
        st.stop()

st.title("🧬 Maize Gene Description Agent")

# Sidebar
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Enter your Google Gemini API Key.")

# Model Selection
model_options = [
    "gemini-2.0-flash",
    "gemini-2.0-pro-exp-02-05", # Updated Pro
    "gemini-1.5-pro",
    "gemini-1.5-flash", 
    "gemini-2.5-pro", # Experimental
]
model_name = st.sidebar.selectbox("Choose Model", model_options, index=0)

if not api_key:
    st.warning("⚠️ Please enter your Gemini API Key in the sidebar to proceed.")
    st.stop()

agent = get_agent(api_key, model_name)

st.markdown("Enter a maize gene ID (e.g., `Zm00001eb126570`, `Zm00001d049294`) to generate a deep functional summary.")

# Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input
if prompt := st.chat_input("Enter Gene ID"):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Searching databases and checking for aliases (this may take 30-60s)...")
        
        try:
            # Capture stdout to show logs? For now, just run it.
            # Using spinner for better UX during long running task
            with st.spinner("Analyzing gene metadata, orthologs, and literature..."):
                 response = agent.generate_description(prompt.strip())
            
            message_placeholder.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            
        except Exception as e:
            error_message = f"**Error**: {str(e)}"
            message_placeholder.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
