from __future__ import annotations

import json

import requests
import streamlit as st


st.set_page_config(page_title="NeuroGuard AI", page_icon="🧠")
st.title("🧠 NeuroGuard AI")
st.caption("Adaptive concussion recovery assistant — clinical decision support, not medical advice.")

api_url = st.sidebar.text_input("Backend URL", "http://127.0.0.1:8000")
input_text = st.text_area("Describe symptoms", placeholder="Example: mild headache and fatigue after injury")

if st.button("Analyze", type="primary"):
    if not input_text.strip():
        st.warning("Enter a symptom description first.")
    else:
        try:
            response = requests.post(f"{api_url.rstrip('/')}/analyze", json={"input_text": input_text}, timeout=30)
            response.raise_for_status()
            result = response.json()
            safe = result["safe"]
            if safe["emergency"]:
                st.error(safe["escalation_message"])
            elif not safe["safe"]:
                st.warning("The generated content was blocked by the safety layer.")
            st.subheader("Symptoms")
            st.json(result["symptoms"])
            st.subheader("Risk")
            st.metric("Risk level", result["risk"]["risk_level"].upper(), f"{result['risk']['score']}/100")
            st.write(result["risk"]["factors"])
            st.subheader("Recovery plan")
            st.json(result["plan"])
            st.subheader("Explanation")
            st.write(result["explanation"])
            st.info(safe["disclaimer"])
        except requests.RequestException as error:
            st.error(f"Could not reach the backend: {error}")
