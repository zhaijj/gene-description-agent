import pandas as pd
import os
import datetime
import streamlit as st

FEEDBACK_FILE = "feedback.csv"

class Feedback:
    def __init__(self):
        self.file_path = FEEDBACK_FILE
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.file_path):
            # rating: 1 (thumbs up) or 0 (thumbs down)
            df = pd.DataFrame(columns=["timestamp", "gene_id", "rating"])
            df.to_csv(self.file_path, index=False)

    def log_feedback(self, gene_id, rating):
        """
        Log feedback for a specific gene ID.
        rating: 1 (thumbs up) or 0 (thumbs down)
        """
        try:
            timestamp = datetime.datetime.now().isoformat()
            
            # Map streamlit feedback values if needed (thumbs returns 1 for up, 0 for down)
            # If use 'faces', it returns index. 'thumbs' is straightforward.
            
            new_entry = {
                "timestamp": timestamp,
                "gene_id": gene_id,
                "rating": rating
            }

            df = pd.DataFrame([new_entry])
            df.to_csv(self.file_path, mode='a', header=False, index=False)
            # Optional: Show a toast
            st.toast("Thank you for your feedback!", icon="🙏")
            
        except Exception as e:
            st.error(f"Error saving feedback: {e}")
