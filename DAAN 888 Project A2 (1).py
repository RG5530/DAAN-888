#!/usr/bin/env python
# coding: utf-8

# In[9]:

import ast
from io import StringIO
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

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


def load_predictions(file_or_path):
    """Load predictions: supports standard CSV or line-based ['file', 'value'] rows."""
    if hasattr(file_or_path, "read"):
        raw = file_or_path.read()
        if isinstance(raw, bytes):
            content = raw.decode("utf-8", errors="replace")
        else:
            content = raw
        if hasattr(file_or_path, "seek"):
            file_or_path.seek(0)
    else:
        content = Path(file_or_path).read_text(encoding="utf-8", errors="replace")
            rows = []
    for line in content.splitlines():
        line = line.strip()
        if not line or not line.startswith("["):
            continue
        try:
            pair = ast.literal_eval(line)
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                rows.append(
                    {"source_file": str(pair[0]), "predicted_zhvi": float(pair[1])}
                )
        except (ValueError, SyntaxError, TypeError):
            continue

    if rows:
        df = pd.DataFrame(rows)
        df["forecast_step"] = range(1, len(df) + 1)
        return df
        
    buf = StringIO(content)
    return pd.read_csv(buf)


st.sidebar.header("Load mode")
mode = st.sidebar.radio("Choose how to load files", ["Use local files", "Upload files"])

if mode == "Use local files":
    monthly_path = BASE_DIR / "testFinal Monthly Data Rev9 (History and Forecast) (2).csv"
    pred_path = BASE_DIR / "testpredictions.csv"
    view_path = BASE_DIR / "testView Data 1.csv"

    missing = [p.name for p in [monthly_path, pred_path, view_path] if not p.exists()]
    if missing:
        st.error(
            "Missing local file(s):\n- " + "\n- ".join(missing)
            + "\n\nPut them in the same folder as `app.py`, or switch to Upload files."
        )
        st.stop()
    Monthly_data = load_csv(monthly_path)
    Predictions_data = load_predictions(pred_path)
    View_data = load_csv(view_path)

else:
    monthly_file = st.sidebar.file_uploader("Monthly CSV", type=["csv"])
    pred_file = st.sidebar.file_uploader("Predictions CSV", type=["csv"])
    view_file = st.sidebar.file_uploader("View Data CSV", type=["csv"])

    if not (monthly_file and pred_file and view_file):
        st.info("Upload all 3 CSV files to continue.")
        st.stop()

    Monthly_data = load_csv(monthly_file)
    Predictions_data = load_predictions(pred_file)
    View_data = load_csv(view_file)

View_data = View_data.rename(columns={"Zip_Code": "Zip Code"})

# --- Prepare columns for charts ---
if "Date" in Monthly_data.columns:
    Monthly_data = Monthly_data.copy()
    Monthly_data["Date"] = pd.to_datetime(Monthly_data["Date"], errors="coerce")

if "Data_Date" in View_data.columns:
    View_data = View_data.copy()
    View_data["Data_Date"] = pd.to_datetime(View_data["Data_Date"], errors="coerce")

zip_col_monthly = "Zip Code" if "Zip Code" in Monthly_data.columns else None
if zip_col_monthly is None and "Zip_Code" in Monthly_data.columns:
    Monthly_data = Monthly_data.rename(columns={"Zip_Code": "Zip Code"})
    zip_col_monthly = "Zip Code"

# ---------------------------------------------------------------------------
# Sidebar: chart options
# ---------------------------------------------------------------------------
st.sidebar.header("Charts")
if zip_col_monthly:
    zips_all = sorted(Monthly_data["Zip Code"].dropna().astype(str).unique())
    default_pick = zips_all[: min(3, len(zips_all))]
    selected_zips = st.sidebar.multiselect(
        "Zip codes — monthly ZHVI",
        options=zips_all,
        default=default_pick,
    )
else:
    selected_zips = []
    st.sidebar.caption("No zip column found in monthly data.")

numeric_view = View_data.select_dtypes(include=["number"]).columns.tolist()

SCHOOL_COLUMN_CANDIDATES = [
    "Schools_Per_SqMile",
    "Total_Schools",
    "Charter_Schools",
    "High_Schools",
]
school_numeric = [
    c for c in SCHOOL_COLUMN_CANDIDATES
    if c in View_data.columns and pd.api.types.is_numeric_dtype(View_data[c])
]
extra_school = [
    c
    for c in numeric_view
    if "school" in c.lower() and c not in school_numeric and c != "Target_ZHVI"
]
school_metrics_for_zhvi = school_numeric + extra_school

st.sidebar.subheader("Scatter (View data)")
x_col = st.sidebar.selectbox("X axis", numeric_view or ["—"], index=0)
_y_idx = 1 if len(numeric_view) > 1 else 0
y_col = st.sidebar.selectbox("Y axis", numeric_view or ["—"], index=_y_idx)
st.sidebar.subheader("Schools vs Target ZHVI")
show_school_trend = st.sidebar.checkbox("Show linear trend (schools chart)", value=True)
school_x_metric = None
if school_metrics_for_zhvi and "Target_ZHVI" in View_data.columns:
    _def_school = (
        "Schools_Per_SqMile"
        if "Schools_Per_SqMile" in school_metrics_for_zhvi
        else school_metrics_for_zhvi[0]
    )
    school_x_metric = st.sidebar.selectbox(
        "School metric (X axis)",
        options=school_metrics_for_zhvi,
        index=school_metrics_for_zhvi.index(_def_school),
    )
    elif "Target_ZHVI" not in View_data.columns:
    st.sidebar.caption("Target_ZHVI missing — schools chart disabled.")
else:
    st.sidebar.caption("No school numeric columns found in View data.")

# ---------------------------------------------------------------------------
# Tabs: tables vs visuals
# ---------------------------------------------------------------------------
tab_viz, tab_tables = st.tabs(["Visualizations", "Data tables"])

with tab_viz:
    st.header("Visualizations")

    # --- Monthly: ZHVI time series (history vs forecast) ---
if zip_col_monthly and selected_zips and "ZHVI" in Monthly_data.columns:
        m_sub = Monthly_data[
            Monthly_data["Zip Code"].astype(str).isin(selected_zips)
        ].dropna(subset=["Date"])

        if not m_sub.empty:
            st.subheader("Monthly ZHVI over time")
            base = (
                alt.Chart(m_sub)
                .mark_line(point=False)
                .encode(
                    alt.X("Date:T", title="Date"),
                    alt.Y("ZHVI:Q", title="ZHVI", scale=alt.Scale(zero=False)),
                    alt.Color("Zip Code:N", title="Zip"),
                    alt.StrokeDash(
                        "Data_Source:N",
                        title="Source",
                        sort=["Historical", "Forecast"],
                    ),
                )
                .properties(height=320)
                .interactive()
            )

            band_cols = {"ZHVI_Upper", "ZHVI_Lower"}.issubset(m_sub.columns)
            if band_cols:
                band = (
                    alt.Chart(m_sub)
                     .mark_area(opacity=0.2)
                    .encode(
                        alt.X("Date:T"),
                        alt.Y("ZHVI_Upper:Q", title="ZHVI"),
                        alt.Y2("ZHVI_Lower:Q"),
                        alt.Color("Zip Code:N"),
                    )
                )
                st.altair_chart(band + base, use_container_width=True)
            else:
                st.altair_chart(base, use_container_width=True)
        else:
            st.warning("No rows for the selected zip code(s).")
    elif not selected_zips:
        st.info("Select at least one zip code in the sidebar to plot monthly ZHVI.")

    # --- View: ZHVI over time (one zip) ---
    if "Target_ZHVI" in View_data.columns and "Data_Date" in View_data.columns:
        st.subheader("View data — Target ZHVI over time")
        vz = View_data.dropna(subset=["Data_Date", "Target_ZHVI"])
        if "Zip Code" in vz.columns:
            v_zips = sorted(vz["Zip Code"].dropna().astype(str).unique())
             pick_v = st.selectbox("Zip for View time series", v_zips, key="view_ts_zip")
            vz_one = vz[vz["Zip Code"].astype(str) == pick_v]
        else:
            vz_one = vz

        if not vz_one.empty:
            ch = (
                alt.Chart(vz_one)
                .mark_line(point=True)
                .encode(
                    alt.X("Data_Date:T", title="Date"),
                    alt.Y("Target_ZHVI:Q", title="Target ZHVI", scale=alt.Scale(zero=False)),
                )
                .properties(height=280)
                .interactive()
            )
            st.altair_chart(ch, use_container_width=True)

    # --- View: scatter ---
    if numeric_view and x_col != y_col and x_col != "—" and y_col != "—":
        st.subheader("View data — scatter")
        sc = (
            alt.Chart(View_data.dropna(subset=[x_col, y_col]))
            .mark_circle(size=40, opacity=0.5)
            .encode(
                alt.X(f"{x_col}:Q", title=x_col),
                alt.Y(f"{y_col}:Q", title=y_col),
                tooltip=[x_col, y_col]
                + ([c for c in ["Zip Code", "Data_Date"] if c in View_data.columns]),
            )
             .properties(height=320)
            .interactive()
        )
        st.altair_chart(sc, use_container_width=True)

    # --- Schools vs Target ZHVI ---
    if school_x_metric and "Target_ZHVI" in View_data.columns:
        st.subheader("Schools vs Target ZHVI")
        s_df = View_data.dropna(subset=[school_x_metric, "Target_ZHVI"]).copy()
        if s_df.empty:
            st.warning(f"No rows with both `{school_x_metric}` and `Target_ZHVI`.")
        else:
            tip = [school_x_metric, "Target_ZHVI"] + [
                c for c in ["Zip Code", "Data_Date"] if c in s_df.columns
            ]
            pts = (
                alt.Chart(s_df)
                .mark_circle(size=48, opacity=0.55, color="#1f77b4")
                .encode(
                    alt.X(f"{school_x_metric}:Q", title=school_x_metric),
                    alt.Y(
                        "Target_ZHVI:Q",
                        title="Target ZHVI",
                        scale=alt.Scale(zero=False),
                    ),
                     tooltip=tip,
                )
            )
            layers = [pts]
            if show_school_trend and len(s_df) >= 2:
                trend = (
                    alt.Chart(s_df)
                    .transform_regression(
                        school_x_metric,
                        "Target_ZHVI",
                    )
                    .mark_line(color="#c0392b", strokeWidth=2)
                    .encode(
                        alt.X(f"{school_x_metric}:Q"),
                        alt.Y("Target_ZHVI:Q", scale=alt.Scale(zero=False)),
                    )
                )
                layers.append(trend)
            st.altair_chart(
                alt.layer(*layers).properties(height=340).interactive(),
                use_container_width=True,
            )
# --- Predictions sequence ---
    pred_y = None
    for c in ("predicted_zhvi", "ZHVI", "prediction", "value"):
        if c in Predictions_data.columns:
            pred_y = c
            break
    if pred_y is None and len(Predictions_data.columns) == 1:
        pred_y = Predictions_data.columns[0]

    if pred_y is not None:
        st.subheader("Predictions file — forecast values")
        p_df = Predictions_data.copy()
        if "forecast_step" in p_df.columns:
            x_enc = alt.X("forecast_step:Q", title="Step")
        else:
            p_df = p_df.reset_index().rename(columns={"index": "forecast_step"})
            x_enc = alt.X("forecast_step:Q", title="Row index")

        pred_chart = (
            alt.Chart(p_df)
            .mark_line(point=True)
            .encode(
                x_enc,
                alt.Y(f"{pred_y}:Q", title=pred_y, scale=alt.Scale(zero=False)),
            )
            .properties(height=280)
            .interactive()
        )
        st.altair_chart(pred_chart, use_container_width=True)
        with tab_tables:
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




