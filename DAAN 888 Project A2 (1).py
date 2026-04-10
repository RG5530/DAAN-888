#!/usr/bin/env python
# coding: utf-8

# In[9]:


# app.py
import pandas as pd
import streamlit as st
from pathlib import Path
st.set_page_config(page_title="DAAN 888 Data Loader", layout="wide")
st.title("DAAN 888 — Load & Inspect CSVs")
BASE_DIR = Path(__file__).resolve().parent
st.sidebar.header("Load mode")
mode = st.sidebar.radio("Choose how to load files", ["Use local files", "Upload files"])
def load_csv(file_or_path):
    return pd.read_csv(file_or_path)
if mode == "Use local files":
    monthly_path = BASE_DIR / "testFinal Monthly Data Rev9 (History and Forecast) (2).csv"
    pred_path = BASE_DIR / "testpredictions.csv"
    view_path = BASE_DIR / "testView Data 1.csv"
    missing = [p.name for p in [monthly_path, pred_path, view_path] if not p.exists()]
    if missing:
        st.error(
            "Missing local file(s):\n- " + "\n- ".join(missing) +
            "\n\nPut them in the same folder as `app.py`, or switch to Upload files."
        )
        st.stop()
    Monthly_data = load_csv(monthly_path)
    Predictions_data = load_csv(pred_path)
    View_data = load_csv(view_path)
else:
    monthly_file = st.sidebar.file_uploader("Monthly CSV", type=["csv"])
    pred_file = st.sidebar.file_uploader("Predictions CSV", type=["csv"])
    view_file = st.sidebar.file_uploader("View Data CSV", type=["csv"])
    if not (monthly_file and pred_file and view_file):
        st.info("Upload all 3 CSV files to continue.")
        st.stop()
    Monthly_data = load_csv(monthly_file)
    Predictions_data = load_csv(pred_file)
    View_data = load_csv(view_file)
# Rename column (safe if it doesn't exist)
View_data = View_data.rename(columns={"Zip_Code": "Zip Code"})
st.subheader("View_data preview")
st.dataframe(View_data.head(20), use_container_width=True)
col1, col2 = st.columns(2)
with col1:
    st.subheader("View_data.describe()")
    st.dataframe(View_data.describe(include="all"), use_container_width=True)
with col2:
    st.subheader("View_data.columns")
    st.write(list(View_data.columns))
with st.expander("Monthly_data preview"):
    st.dataframe(Monthly_data.head(20), use_container_width=True)
with st.expander("Predictions_data preview"):
    st.dataframe(Predictions_data.head(20), use_container_width=True)


# In[ ]:




