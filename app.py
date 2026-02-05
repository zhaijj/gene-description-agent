import traceback
import streamlit as st
import importlib
import src.agent
importlib.reload(src.agent)
from src.agent import GeneDescriptionAgent
from src.analytics import Analytics

# Initialize the agent
def get_agent(api_key, model_name):
    try:
        return GeneDescriptionAgent(api_key=str(api_key), model_name=model_name)
    except Exception as e:
        st.error(f"Failed to initialize Agent: {e}")
        st.code(traceback.format_exc())
        st.stop()


# Initialize Analytics
analytics = Analytics()
analytics.track_user()

# Initialize Feedback
from src.feedback import Feedback
feedback_manager = Feedback()

st.title("🧬 Maize Gene Description Agent")

# Sidebar
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Enter your Google Gemini API Key.")


# Model Selection
# Verified working models based on local test
model_options = [
    "gemini-2.5-pro",        # Best Reasoning (Default)
    "gemini-2.5-flash",      # High Speed
    "gemini-3-flash-preview",# Experimental (Flash)
    "gemini-3-pro-preview",  # Experimental (Pro)
]
model_name = st.sidebar.selectbox("Choose Model", model_options, index=0)

# Analytics Section (Default Expanded)
# Using an expander is cleaner than a checkbox if it's "on by default" but collapsible
with st.sidebar.expander("📊 Traffic Analytics", expanded=True):
    analytics.display_analytics()

# General Feedback/Comments
with st.sidebar.expander("💬 Leave a Comment"):
    comment_text = st.text_area("Share your thoughts, suggestions, or report bugs:", height=100)
    if st.button("Submit Feedback"):
        if comment_text.strip():
            feedback_manager.log_comment(comment_text)
        else:
            st.warning("Please enter some text.")

if not api_key:
    st.warning("⚠️ Please enter your Gemini API Key in the sidebar to proceed.")
    st.stop()

agent = get_agent(api_key, model_name)

st.markdown("Enter a maize gene ID (e.g., `Zm00001eb126570`, `Zm00001d049294`) to generate a deep functional summary.")

# Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display feedback button for assistant messages if gene_id is present
        if message["role"] == "assistant" and "gene_id" in message:
            def on_feedback_submit(idx=idx, gene_id=message["gene_id"]):
                # Get the value from session state using the key
                key = f"feedback_{idx}"
                if key in st.session_state:
                    rating = 1 if st.session_state[key] == "thumbs_up" else 0
                    feedback_manager.log_feedback(gene_id, rating)

            st.feedback(
                "thumbs",
                key=f"feedback_{idx}",
                on_change=on_feedback_submit,
                args=(idx, message["gene_id"]) # dummy args, using closure above or session state
            )
            
            # Download Button
            st.download_button(
                label="📥 Download Report",
                data=message["content"],
                file_name=f"{message['gene_id']}_description.md",
                mime="text/markdown",
                key=f"download_{idx}"
            )

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
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response,
                "gene_id": prompt.strip() # Store gene_id for feedback context
            })
            
            # Show feedback widget for the new message immediately
            # The current message is the last one in session_state
            # But st.feedback needs a key. We can rerender or just let the loop handle it on next run?
            # Better to show it now.
            # Using a simple key based on length
            new_idx = len(st.session_state.messages) - 1
            
            def on_new_feedback_submit():
                key = f"feedback_{new_idx}"
                if key in st.session_state:
                     rating = 1 if st.session_state[key] == "thumbs_up" else 0
                     feedback_manager.log_feedback(prompt.strip(), rating)

            st.feedback(
                "thumbs", 
                key=f"feedback_{new_idx}",
                on_change=on_new_feedback_submit
            )
            
            # Download Button for the new message
            st.download_button(
                label="📥 Download Report",
                data=response,
                file_name=f"{prompt.strip()}_description.md",
                mime="text/markdown",
                key=f"download_{new_idx}"
            )
            
        except Exception as e:
            error_message = f"**Error**: {str(e)}"
            message_placeholder.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
