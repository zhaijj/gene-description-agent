import streamlit as st
import pandas as pd
import os
import datetime
import requests
from streamlit_javascript import st_javascript

ANALYTICS_FILE = "analytics.csv"

class Analytics:
    def __init__(self):
        self.file_path = ANALYTICS_FILE
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.file_path):
            df = pd.DataFrame(columns=["timestamp", "ip", "city", "country", "latitude", "longitude"])
            df.to_csv(self.file_path, index=False)

    def _get_location(self):
        try:
            url = 'https://get.geojs.io/v1/ip/geo.json'
            # streamlit-javascript to handle client-side execution if needed, 
            # but for simplicity and reliability in python backend (if not strictly client-side only constraint),
            # we can try fetching. 
            # However, running in cloud, request.ip is server ip. 
            # We need client IP. 
            # streamlit_javascript is useful for execution but getting return value can be tricky with reruns.
            # Let's try a direct approach using st_javascript to fetch and return.
            
            # Actually, standard pattern uses a js fetch.
            # For this MVP, let's use a simpler approach that might count server requests if running locally,
            # but in a real web context, we need the headers. 
            # Streamlit doesn't expose headers easily.
            # Let's use `streamlit-javascript` to get the data client side.
            
            js_code = """fetch("https://get.geojs.io/v1/ip/geo.json").then(response => response.json())"""
            return st_javascript(js_code)
        except Exception as e:
            print(f"Error fetching location: {e}")
            return None

    def track_user(self):
        # Avoid duplicate counting in same session
        if "analytics_tracked" in st.session_state:
            return

        loc_data = self._get_location()
        
        if loc_data and isinstance(loc_data, dict):
            timestamp = datetime.datetime.now().isoformat()
            ip = loc_data.get("ip", "unknown")
            city = loc_data.get("city", "unknown")
            country = loc_data.get("country", "unknown")
            lat = loc_data.get("latitude", 0.0)
            lon = loc_data.get("longitude", 0.0)

            new_entry = {
                "timestamp": timestamp,
                "ip": ip,
                "city": city,
                "country": country,
                "latitude": lat,
                "longitude": lon
            }

            # Append to file
            df = pd.DataFrame([new_entry])
            df.to_csv(self.file_path, mode='a', header=False, index=False)
            
            st.session_state["analytics_tracked"] = True

    def display_analytics(self):
        if not os.path.exists(self.file_path):
            st.warning("No analytics data available yet.")
            return

        try:
            df = pd.read_csv(self.file_path)
            if df.empty:
                st.warning("No analytics data recorded.")
                return

            # Basic Metrics
            total_visits = len(df)
            unique_visitors = df['ip'].nunique()
            unique_countries = df['country'].nunique()

            st.markdown("### 📊 Live Traffic")
            # For sidebar, single column metrics are better or use delta
            col1, col2 = st.columns(2)
            col1.metric("Visits", total_visits)
            col2.metric("Unique", unique_visitors)
            st.metric("Countries", unique_countries)

            # Map
            st.markdown("### 🌍 Visitor Map")
            # Ensure lat/lon are numeric
            df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
            df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
            
            map_data = df.dropna(subset=['latitude', 'longitude'])
            if not map_data.empty:
                st.map(map_data, size=20, zoom=1)
            else:
                st.info("No location data to display on map.")

            # Recent visits table (optional, maybe hidden in expander)
            with st.expander("See recent visits"):
                st.dataframe(df.tail(5)[['city', 'country']], hide_index=True)
                
        except Exception as e:
            st.error(f"Error loading analytics: {e}")
