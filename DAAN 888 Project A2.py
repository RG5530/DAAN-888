#!/usr/bin/env python
# coding: utf-8

# In[1]:


"""
Created on Thu Apr  9 08:10:59 2026

@author: rache
"""
#pip install plotly
#pip install pandas
#pip install streamlit
import pandas as pd
import streamlit as st
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import ast


# In[2]:


st.set_page_config(page_title="DAAN 888 Data Explorer", layout="wide")
st.title("📊 DAAN 888 — Housing Data Explorer")

BASE_DIR = Path(__file__).resolve().parent


# In[3]:


# Sidebar controls
st.sidebar.header("⚙️ Configuration")
mode = st.sidebar.radio("Choose how to load files", ["Use local files", "Upload files"])

def load_csv(file_or_path):
    return pd.read_csv(file_or_path)

def parse_predictions_data(file_or_path):
    """Parse predictions CSV with special formatting"""
    with open(file_or_path, 'r') as f:
        data = []
        for line in f:
            line = line.strip()
            if line:
                try:
                    parsed = ast.literal_eval(line)
                    if isinstance(parsed, list) and len(parsed) == 2:
                        data.append({'Source': parsed[0], 'Prediction': float(parsed[1])})
                except:
                    pass
    return pd.DataFrame(data)


# In[4]:


# Load data
if mode == "Use local files":
    monthly_path = BASE_DIR / "testFinal Monthly Data Rev9 (History and Forecast) (2).csv"
    pred_path = BASE_DIR / "testpredictions.csv"
    view_path = BASE_DIR / "testView Data 1.csv"
    
    missing = [p.name for p in [monthly_path, pred_path, view_path] if not p.exists()]
    if missing:
        st.error(
            "Missing local file(s):\n- " + "\n- ".join(missing) +
            "\n\nPut them in the same folder as the script, or switch to Upload files."
        )
        st.stop()
    
    monthly_data = load_csv(monthly_path)
    predictions_data = parse_predictions_data(pred_path)
    view_data = load_csv(view_path)
else:
    monthly_file = st.sidebar.file_uploader("Monthly CSV", type=["csv"])
    pred_file = st.sidebar.file_uploader("Predictions CSV", type=["csv"])
    view_file = st.sidebar.file_uploader("View Data CSV", type=["csv"])
    
    if not (monthly_file and pred_file and view_file):
        st.info("📤 Upload all 3 CSV files to continue.")
        st.stop()
    
    monthly_data = load_csv(monthly_file)
    
    # Save temp file for predictions
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        tmp.write(pred_file.read().decode())
        tmp_path = tmp.name
    predictions_data = parse_predictions_data(tmp_path)
    
    view_data = load_csv(view_file)


# In[5]:


# Standardize column names
if "Zip_Code" in view_data.columns:
    view_data = view_data.rename(columns={"Zip_Code": "Zip Code"})

# Create tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "🏘️ Monthly Data", "🔮 Predictions", "📊 View Data"])

# Tab 1: Overview
with tab1:
    st.subheader("Dataset Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Monthly Data Rows", len(monthly_data))
        if 'Zip Code' in monthly_data.columns:
            st.metric("Unique Zip Codes", monthly_data['Zip Code'].nunique())
    
    with col2:
        st.metric("View Data Rows", len(view_data))
        st.metric("View Data Features", len(view_data.columns))
    
    with col3:
        st.metric("Predictions", len(predictions_data))
        avg_pred = predictions_data['Prediction'].mean() if len(predictions_data) > 0 else 0
        st.metric("Average Prediction", f"${avg_pred:,.0f}")
    
    # Quick statistics
    st.subheader("Key Statistics")
    st.write("**Monthly Data - ZHVI**")
    if 'ZHVI' in monthly_data.columns:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Min", f"${monthly_data['ZHVI'].min():,.0f}")
        with col2:
            st.metric("Max", f"${monthly_data['ZHVI'].max():,.0f}")
        with col3:
            st.metric("Mean", f"${monthly_data['ZHVI'].mean():,.0f}")
        with col4:
            st.metric("Median", f"${monthly_data['ZHVI'].median():,.0f}")


# In[6]:


# Tab 2: Monthly Data
with tab2:
    st.subheader("Monthly Housing Data (History & Forecast)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Data Preview**")
        st.dataframe(monthly_data.head(15), use_container_width=True)
    
    with col2:
        st.write("**Statistics**")
        numeric_cols = monthly_data.select_dtypes(include=['number']).columns
        st.dataframe(monthly_data[numeric_cols].describe(), use_container_width=True)
    
    # Visualizations
    if 'ZHVI' in monthly_data.columns and 'Date' in monthly_data.columns:
        st.subheader("ZHVI Trend Over Time")
        try:
            monthly_data_plot = monthly_data.copy()
            monthly_data_plot['Date'] = pd.to_datetime(monthly_data_plot['Date'], errors='coerce')
            monthly_data_plot = monthly_data_plot.sort_values('Date')
            
            # Separate historical and forecast
            hist = monthly_data_plot[monthly_data_plot['Data_Source'] == 'Historical']
            forecast = monthly_data_plot[monthly_data_plot['Data_Source'] == 'Forecast']
            
            fig = go.Figure()
            if len(hist) > 0:
                fig.add_trace(go.Scatter(x=hist['Date'], y=hist['ZHVI'], 
                                        name='Historical', mode='lines', line=dict(color='blue')))
            if len(forecast) > 0:
                fig.add_trace(go.Scatter(x=forecast['Date'], y=forecast['ZHVI'], 
                                        name='Forecast', mode='lines', line=dict(color='red', dash='dash')))
            
            fig.update_layout(title='ZHVI Over Time', xaxis_title='Date', yaxis_title='ZHVI', 
                            hovermode='x unified', height=500)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not plot data: {e}")
    
    # Data source breakdown
    if 'Data_Source' in monthly_data.columns:
        st.subheader("Data Source Breakdown")
        source_counts = monthly_data['Data_Source'].value_counts()
        fig = px.pie(values=source_counts.values, names=source_counts.index, 
                    title='Historical vs Forecast Data')
        st.plotly_chart(fig, use_container_width=True)


# In[7]:


# Tab 3: Predictions
with tab3:
    st.subheader("Predictions Data")
    
    if len(predictions_data) > 0:
        st.dataframe(predictions_data.head(30), use_container_width=True)
        
        st.subheader("Predictions Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Predictions", len(predictions_data))
        with col2:
            st.metric("Min Prediction", f"${predictions_data['Prediction'].min():,.2f}")
        with col3:
            st.metric("Max Prediction", f"${predictions_data['Prediction'].max():,.2f}")
        
        # Visualization
        st.subheader("Prediction Distribution")
        if len(predictions_data) > 1:
            fig = px.histogram(predictions_data, x='Prediction', nbins=30, 
                             title='Distribution of Predictions')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No predictions data available")


# In[8]:


# Tab 4: View Data
with tab4:
    st.subheader("View Data - Demographics & Metrics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Data Preview**")
        st.dataframe(view_data.head(20), use_container_width=True)
    
    with col2:
        st.write("**Statistical Summary**")
        numeric_cols = view_data.select_dtypes(include=['number']).columns
        st.dataframe(view_data[numeric_cols].describe(), use_container_width=True)
    
    st.subheader("Column Details")
    st.write(f"**Total Columns: {len(view_data.columns)}**")
    st.dataframe(pd.DataFrame({
        'Column': view_data.columns,
        'Data Type': view_data.dtypes.values,
        'Non-Null Count': view_data.count().values,
        'Missing': len(view_data) - view_data.count().values
    }), use_container_width=True)
    
    # Advanced visualizations
    st.subheader("Data Visualizations")
    numeric_cols_list = view_data.select_dtypes(include=['number']).columns.tolist()
    
    if len(numeric_cols_list) >= 2:
        col1, col2 = st.columns(2)
        
        with col1:
            x_col = st.selectbox("Select X-axis", numeric_cols_list, key='x_col')
        with col2:
            y_col = st.selectbox("Select Y-axis", numeric_cols_list, key='y_col', index=1 if len(numeric_cols_list) > 1 else 0)
        
        if x_col and y_col:
            fig = px.scatter(view_data, x=x_col, y=y_col, title=f"{y_col} vs {x_col}",
                           hover_data=view_data.columns[:5])
            st.plotly_chart(fig, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.info(
    "**DAAN 888 Data Explorer**\n\n"
    "Explore housing data, demographics, and predictions."
)



# In[ ]:




