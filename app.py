# app.py

import streamlit as st
from pipeline import load_lightcurve, iterative_tls_search, summarize_results

st.set_page_config(page_title="Exoplanet Explorer", layout="wide")
st.title("🔭 Exoplanet Explorer")

uploaded_file = st.file_uploader("Upload a light curve file (.fits or .csv)", type=["fits", "csv"])

if uploaded_file:
    with st.spinner("Reading light curve..."):
        try:
            lc = load_lightcurve(uploaded_file)
            lc.plot()
            st.pyplot()
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

    if st.button("🔍 Run Transit Search"):
        with st.spinner("Running TLS..."):
            results = iterative_tls_search(lc)

        if results:
            st.success(f"Detected {len(results)} candidate(s)!")
            summary = summarize_results(results)
            st.table(summary)
        else:
            st.warning("No significant transit signals found.")

st.markdown("---")
st.markdown("Made with ❤️ using [Lightkurve](https://docs.lightkurve.org/) + [TransitLeastSquares](https://transitleastsquares.readthedocs.io/en/latest/) + Streamlit.")

