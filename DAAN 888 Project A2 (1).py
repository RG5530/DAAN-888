#!/usr/bin/env python
# coding: utf-8

from __future__ import annotations

import ast
import io
from io import StringIO
from pathlib import Path
from typing import NamedTuple

import altair as alt
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent

MONTHLY_CSV = "testFinal Monthly Data Rev9 (History and Forecast) (2).csv"
PREDICTIONS_CSV = "testpredictions.csv"
VIEW_CSV = "testView Data 1.csv"

SCHOOL_COLUMN_CANDIDATES = [
    "Schools_Per_SqMile",
    "Total_Schools",
    "Charter_Schools",
    "High_Schools",
]


def _read_text_from_path_or_fileobj(file_or_path: Path | object) -> str:
    if isinstance(file_or_path, Path):
        return file_or_path.read_text(encoding="utf-8", errors="replace")
    raw = file_or_path.read()
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return raw


def _rewind_if_possible(file_or_path: object) -> None:
    if hasattr(file_or_path, "seek"):
        try:
            file_or_path.seek(0)
        except (OSError, io.UnsupportedOperation):
            pass


def load_standard_csv(file_or_path: Path | object) -> pd.DataFrame:
    if isinstance(file_or_path, Path):
        return pd.read_csv(file_or_path)
    _rewind_if_possible(file_or_path)
    return pd.read_csv(file_or_path)


def load_predictions_csv(file_or_path: Path | object) -> pd.DataFrame:
    content = _read_text_from_path_or_fileobj(file_or_path)
    _rewind_if_possible(file_or_path)

    rows: list[dict[str, object]] = []
    for line in content.splitlines():
        line = line.strip()
        if not line or not line.startswith("["):
            continue
        try:
            pair = ast.literal_eval(line)
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                rows.append(
                    {
                        "source_file": str(pair[0]),
                        "predicted_zhvi": float(pair[1]),
                    }
                )
        except (ValueError, SyntaxError, TypeError):
            continue

    if rows:
        df = pd.DataFrame(rows)
        df["forecast_step"] = range(1, len(df) + 1)
        return df

    return pd.read_csv(StringIO(content))


def local_csv_paths(base: Path) -> dict[str, Path]:
    return {
        "monthly": base / MONTHLY_CSV,
        "predictions": base / PREDICTIONS_CSV,
        "view": base / VIEW_CSV,
    }


def load_all_from_local(base: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    paths = local_csv_paths(base)
    missing = [p.name for p in paths.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("\n- ".join(["Missing local file(s):"] + missing))

    monthly = load_standard_csv(paths["monthly"])
    predictions = load_predictions_csv(paths["predictions"])
    view = load_standard_csv(paths["view"])
    return monthly, predictions, view


def load_all_from_uploads(
    monthly_file: object,
    predictions_file: object,
    view_file: object,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        load_standard_csv(monthly_file),
        load_predictions_csv(predictions_file),
        load_standard_csv(view_file),
    )


class PreparedData(NamedTuple):
    monthly: pd.DataFrame
    predictions: pd.DataFrame
    view: pd.DataFrame
    zip_col_monthly: str | None
    numeric_view: list[str]
    school_metrics_for_zhvi: list[str]


def prepare_datasets(
    monthly: pd.DataFrame,
    predictions: pd.DataFrame,
    view: pd.DataFrame,
) -> PreparedData:
    view = view.rename(columns={"Zip_Code": "Zip Code"})

    monthly = monthly.copy()
    if "Date" in monthly.columns:
        monthly["Date"] = pd.to_datetime(monthly["Date"], errors="coerce")

    view = view.copy()
    if "Data_Date" in view.columns:
        view["Data_Date"] = pd.to_datetime(view["Data_Date"], errors="coerce")

    zip_col_monthly: str | None = None
    if "Zip Code" in monthly.columns:
        zip_col_monthly = "Zip Code"
    elif "Zip_Code" in monthly.columns:
        monthly = monthly.rename(columns={"Zip_Code": "Zip Code"})
        zip_col_monthly = "Zip Code"

    numeric_view = view.select_dtypes(include=["number"]).columns.tolist()

    school_numeric = [
        c
        for c in SCHOOL_COLUMN_CANDIDATES
        if c in view.columns and pd.api.types.is_numeric_dtype(view[c])
    ]
    extra_school = [
        c
        for c in numeric_view
        if "school" in c.lower() and c not in school_numeric and c != "Target_ZHVI"
    ]

    return PreparedData(
        monthly=monthly,
        predictions=predictions,
        view=view,
        zip_col_monthly=zip_col_monthly,
        numeric_view=numeric_view,
        school_metrics_for_zhvi=school_numeric + extra_school,
    )


def predictions_value_column(pred_df: pd.DataFrame) -> str | None:
    for c in ("predicted_zhvi", "ZHVI", "prediction", "value"):
        if c in pred_df.columns:
            return c
    if len(pred_df.columns) == 1:
        return pred_df.columns[0]
    return None


# --- Streamlit ---
st.set_page_config(page_title="DAAN 888 Dashboard", layout="wide")
st.title("DAAN 888 — Monthly, predictions & view data")
st.caption(
    "Loads the same three CSVs as your notebook: monthly history/forecast, predictions, and view data "
    "(with `Zip_Code` renamed to `Zip Code`)."
)

st.sidebar.header("Load data")
mode = st.sidebar.radio("Source", ["Use local files", "Upload files"])

if mode == "Use local files":
    try:
        Monthly_data, Predictions_data, View_data = load_all_from_local(BASE_DIR)
    except FileNotFoundError as e:
        st.error(str(e))
        st.caption(
            f"Place these next to `app.py` in:\n`{BASE_DIR}`\n\n"
            f"- `{MONTHLY_CSV}`\n- `{PREDICTIONS_CSV}`\n- `{VIEW_CSV}`"
        )
        st.info("Or choose **Upload files** in the sidebar.")
        st.stop()
else:
    st.sidebar.markdown("Upload all three CSVs.")
    monthly_up = st.sidebar.file_uploader("Monthly CSV", type=["csv"])
    pred_up = st.sidebar.file_uploader("Predictions CSV", type=["csv"])
    view_up = st.sidebar.file_uploader("View data CSV", type=["csv"])
    if not (monthly_up and pred_up and view_up):
        st.info("Upload all three CSV files to continue.")
        st.stop()
    Monthly_data, Predictions_data, View_data = load_all_from_uploads(
        monthly_up, pred_up, view_up
    )

P = prepare_datasets(Monthly_data, Predictions_data, View_data)
Monthly_data = P.monthly
Predictions_data = P.predictions
View_data = P.view

pred_y_col = predictions_value_column(Predictions_data)

st.sidebar.header("Charts")
if P.zip_col_monthly:
    zips_monthly = sorted(Monthly_data["Zip Code"].dropna().astype(str).unique())
    default_pick = zips_monthly[: min(3, len(zips_monthly))]
    selected_zips = st.sidebar.multiselect(
        "Zip codes — monthly ZHVI",
        options=zips_monthly,
        default=default_pick,
    )
else:
    selected_zips = []
    st.sidebar.caption("No zip column in monthly data.")

st.sidebar.subheader("Scatter (View data)")
x_col = st.sidebar.selectbox("X axis", P.numeric_view or ["—"], index=0)
_y_idx = 1 if len(P.numeric_view) > 1 else 0
y_col = st.sidebar.selectbox("Y axis", P.numeric_view or ["—"], index=_y_idx)

st.sidebar.subheader("Schools vs Target ZHVI")
show_school_trend = st.sidebar.checkbox("Linear trend on schools chart", value=True)
school_x_metric: str | None = None
if P.school_metrics_for_zhvi and "Target_ZHVI" in View_data.columns:
    _def = (
        "Schools_Per_SqMile"
        if "Schools_Per_SqMile" in P.school_metrics_for_zhvi
        else P.school_metrics_for_zhvi[0]
    )
    school_x_metric = st.sidebar.selectbox(
        "School metric (X)",
        options=P.school_metrics_for_zhvi,
        index=P.school_metrics_for_zhvi.index(_def),
    )
elif "Target_ZHVI" not in View_data.columns:
    st.sidebar.caption("Schools chart needs Target_ZHVI.")
else:
    st.sidebar.caption("No school columns in view data.")

tab_overview, tab_viz, tab_pred, tab_data = st.tabs(
    ["Overview", "Visualizations", "Predictions", "Data tables"]
)

# ----- Overview -----
with tab_overview:
    st.header("At a glance")
    c1, c2, c3 = st.columns(3)
    c1.metric("Monthly rows", f"{len(Monthly_data):,}")
    c2.metric("Predictions rows", f"{len(Predictions_data):,}")
    c3.metric("View rows", f"{len(View_data):,}")

    st.subheader("Monthly data (quick facts)")
    if P.zip_col_monthly and "Date" in Monthly_data.columns:
        mc1, mc2, mc3 = st.columns(3)
        n_zips = Monthly_data["Zip Code"].nunique()
        mc1.metric("Zip codes", f"{n_zips:,}")
        dmin = Monthly_data["Date"].min()
        dmax = Monthly_data["Date"].max()
        mc2.metric("Date range (start)", str(dmin.date()) if pd.notna(dmin) else "—")
        mc3.metric("Date range (end)", str(dmax.date()) if pd.notna(dmax) else "—")
        if "Data_Source" in Monthly_data.columns:
            st.write("**Records by source:**")
            st.dataframe(
                Monthly_data["Data_Source"].value_counts().rename_axis("Source").reset_index(name="Count"),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.caption("Monthly file: zip or date columns not detected for summary.")

    st.subheader("Predictions (quick facts)")
    if pred_y_col:
        s = pd.to_numeric(Predictions_data[pred_y_col], errors="coerce").dropna()
        if len(s):
            pc1, pc2, pc3, pc4 = st.columns(4)
            pc1.metric("Forecast steps", f"{len(s):,}")
            pc2.metric("Min value", f"{s.min():,.2f}")
            pc3.metric("Max value", f"{s.max():,.2f}")
            pc4.metric("Mean value", f"{s.mean():,.2f}")
        if "source_file" in Predictions_data.columns:
            st.caption(
                f"Source label (first row): `{Predictions_data['source_file'].iloc[0]}`"
            )
    else:
        st.warning("Could not detect a numeric prediction column.")

    st.subheader("View data (quick facts)")
    if "Target_ZHVI" in View_data.columns:
        tz = pd.to_numeric(View_data["Target_ZHVI"], errors="coerce").dropna()
        if len(tz):
            vc1, vc2 = st.columns(2)
            vc1.metric("Target_ZHVI — mean", f"{tz.mean():,.2f}")
            vc2.metric("Target_ZHVI — median", f"{tz.median():,.2f}")
    st.write("**Column names (View_data):**")
    st.code(", ".join(View_data.columns.astype(str).tolist()), language="text")

# ----- Visualizations -----
with tab_viz:
    st.header("Visualizations")

    if P.zip_col_monthly and selected_zips and "ZHVI" in Monthly_data.columns:
        m_sub = Monthly_data[
            Monthly_data["Zip Code"].astype(str).isin(selected_zips)
        ].dropna(subset=["Date"])
        if not m_sub.empty:
            st.subheader("Monthly ZHVI over time (history vs forecast)")
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
            if {"ZHVI_Upper", "ZHVI_Lower"}.issubset(m_sub.columns):
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
    elif P.zip_col_monthly and not selected_zips:
        st.info("Pick at least one zip in the sidebar for the monthly chart.")

    if "Target_ZHVI" in View_data.columns and "Data_Date" in View_data.columns:
        st.subheader("View data — Target ZHVI over time")
        vz = View_data.dropna(subset=["Data_Date", "Target_ZHVI"])
        if "Zip Code" in vz.columns:
            v_zips = sorted(vz["Zip Code"].dropna().astype(str).unique())
            pick_v = st.selectbox("Zip", v_zips, key="view_ts_zip")
            vz_one = vz[vz["Zip Code"].astype(str) == pick_v]
        else:
            vz_one = vz
        if not vz_one.empty:
            st.altair_chart(
                alt.Chart(vz_one)
                .mark_line(point=True)
                .encode(
                    alt.X("Data_Date:T", title="Date"),
                    alt.Y(
                        "Target_ZHVI:Q",
                        title="Target ZHVI",
                        scale=alt.Scale(zero=False),
                    ),
                )
                .properties(height=280)
                .interactive(),
                use_container_width=True,
            )

    if P.numeric_view and x_col != y_col and x_col != "—" and y_col != "—":
        st.subheader("View data — scatter")
        st.altair_chart(
            alt.Chart(View_data.dropna(subset=[x_col, y_col]))
            .mark_circle(size=40, opacity=0.5)
            .encode(
                alt.X(f"{x_col}:Q", title=x_col),
                alt.Y(f"{y_col}:Q", title=y_col),
                tooltip=[x_col, y_col]
                + [c for c in ["Zip Code", "Data_Date"] if c in View_data.columns],
            )
            .properties(height=320)
            .interactive(),
            use_container_width=True,
        )

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
                layers.append(
                    alt.Chart(s_df)
                    .transform_regression(school_x_metric, "Target_ZHVI")
                    .mark_line(color="#c0392b", strokeWidth=2)
                    .encode(
                        alt.X(f"{school_x_metric}:Q"),
                        alt.Y("Target_ZHVI:Q", scale=alt.Scale(zero=False)),
                    )
                )
            st.altair_chart(
                alt.layer(*layers).properties(height=340).interactive(),
                use_container_width=True,
            )

# ----- Predictions -----
with tab_pred:
    st.header("Predictions")
    st.markdown(
        f"Loaded from **`{PREDICTIONS_CSV}`** (or your upload). "
        "Line-style files are parsed into `predicted_zhvi` and `forecast_step`."
    )

    if pred_y_col is None:
        st.error("No prediction value column found.")
        st.dataframe(Predictions_data.head(50), use_container_width=True)
    else:
        p_df = Predictions_data.copy()
        if "forecast_step" in p_df.columns:
            x_enc = alt.X("forecast_step:Q", title="Step")
        else:
            p_df = p_df.reset_index().rename(columns={"index": "forecast_step"})
            x_enc = alt.X("forecast_step:Q", title="Row index")

        st.subheader("Forecast series")
        st.altair_chart(
            alt.Chart(p_df)
            .mark_line(point=True, color="#2ca02c")
            .encode(
                x_enc,
                alt.Y(f"{pred_y_col}:Q", title=pred_y_col, scale=alt.Scale(zero=False)),
            )
            .properties(height=320)
            .interactive(),
            use_container_width=True,
        )

        st.subheader("Predictions table")
        n_show = st.slider("Rows to show", 10, min(500, max(10, len(p_df))), min(100, len(p_df)))
        st.dataframe(p_df.head(n_show), use_container_width=True)

        csv_bytes = p_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download predictions as CSV",
            data=csv_bytes,
            file_name="predictions_export.csv",
            mime="text/csv",
        )

# ----- Data tables -----
with tab_data:
    st.header("Data tables — head, describe, columns")
    st.markdown("Same exploration as `View_data.head()`, `View_data.describe()`, and `View_data.columns` in your notebook.")

    head_n = st.slider("Rows for `.head()` previews", 5, 50, 10)

    st.subheader("View_data")
    st.dataframe(View_data.head(head_n), use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**describe()**")
        st.dataframe(View_data.describe(include="all"), use_container_width=True)
    with c2:
        st.markdown("**columns**")
        st.write(list(View_data.columns))

    st.subheader("Monthly_data")
    st.dataframe(Monthly_data.head(head_n), use_container_width=True)
    with st.expander("Monthly describe()"):
        st.dataframe(Monthly_data.describe(include="all"), use_container_width=True)
    with st.expander("Monthly columns"):
        st.write(list(Monthly_data.columns))

    st.subheader("Predictions_data")
    st.dataframe(Predictions_data.head(head_n), use_container_width=True)
    with st.expander("Predictions describe()"):
        st.dataframe(Predictions_data.describe(include="all"), use_container_width=True)
    with st.expander("Predictions columns"):
        st.write(list(Predictions_data.columns))



