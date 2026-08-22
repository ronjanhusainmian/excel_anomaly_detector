import os
import tempfile

from dotenv import load_dotenv
import streamlit as st

from src.parser import load_formula_cells, build_blocks
from src.anomaly import detect_anomalies, dedupe_keep_best
from src.explain import explain_anomaly

load_dotenv()  # reads the API key from .env (if present) into os.environ

st.set_page_config(page_title="Excel Formula Anomaly Detector", layout="wide")

st.title("Excel Formula Anomaly Detector")
st.caption(
    "Upload a workbook. This scans every filled-down/filled-across formula block "
    "and flags cells whose formula breaks the pattern the rest of the block follows, "
    "one of the most common source of silent spreadsheet errors."
)

with st.sidebar:
    st.header("Settings")
    min_majority = st.slider(
        "Minimum pattern strength to flag anything",
        min_value=0.5, max_value=0.95, value=0.6, step=0.05,
        help="A block only gets checked if at least this fraction of its cells agree on one pattern.",
    )
    min_block_size = st.slider(
        "Minimum block size", min_value=3, max_value=10, value=3,
        help="Ignore blocks smaller than this - too few cells to establish a reliable pattern.",
    )
    api_key_present = bool(os.environ.get("OPENAI_API_KEY"))
    st.divider()
    if api_key_present:
        st.success("OPENAI_API_KEY detected - AI explanations enabled.")
    else:
        st.warning("No OPENAI_API_KEY set - showing template explanations only.")

uploaded = st.file_uploader("Upload an .xlsx workbook", type=["xlsx"])

if uploaded is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    with st.spinner("Parsing workbook..."):
        cells = load_formula_cells(tmp_path)
        blocks = build_blocks(cells, min_block_size=min_block_size)

    st.write(f"Found **{len(cells)}** formula cells across **{len(blocks)}** checkable blocks.")

    if not cells:
        st.info("No formulas found in this workbook.")
    else:
        with st.spinner("Scanning for anomalies..."):
            anomalies = dedupe_keep_best(
                detect_anomalies(blocks, min_majority_share=min_majority)
            )

        if not anomalies:
            st.success("No anomalies found - every formula block is internally consistent.")
        else:
            st.subheader(f"⚠️ {len(anomalies)} potential issue(s) found")

            for a in anomalies:
                with st.container(border=True):
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.metric("Cell", f"{a.sheet}!{a.address}")
                        st.metric("Confidence", f"{a.confidence:.0%}")
                        st.caption(
                            f"{a.orientation.title()} block of {a.block_size} cells - "
                            f"{a.majority_share:.0%} follow the dominant pattern."
                        )
                    with col2:
                        st.code(a.formula, language=None)
                        if a.example_conforming_cell:
                            st.caption(
                                f"Expected pattern (e.g. {a.example_conforming_cell.address}): "
                                f"`{a.example_conforming_cell.formula}`"
                            )
                        with st.spinner("Explaining..."):
                            explanation = explain_anomaly(a)
                        st.write(explanation)

    os.unlink(tmp_path)
else:
    st.info("Upload an .xlsx file to get started.")
