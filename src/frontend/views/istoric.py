import streamlit as st
import pandas as pd
import sys
import os

# Acest bloc trebuie să fie prezent în FIECARE fișier din folderul "pages/"
# pentru ca acestea să poată vedea codul din "src/backend/"
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)



current_user = st.session_state.current_user

st.markdown("### 📈 Evoluția Biomarkerilor")
st.markdown("Vizualizarea evoluției pe baza analizelor salvate.")

date_istoric = pd.DataFrame(
    {
        "Glicemie (mg/dL)": [95, 105, 115],
        "Sideremie (µg/dL)": [80, 60, 45],
    },
    index=["Octombrie 2025", "Decembrie 2025", "Februarie 2026"],
)
st.line_chart(date_istoric)

st.markdown("#### 📁 Sesiuni anterioare")
with st.expander("Sesiune - Decembrie 2025"):
    st.write("Date preluate din baza de date SQLite.")
