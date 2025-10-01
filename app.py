# app.py

import streamlit as st
from pipeline import load_lightcurve, iterative_tls_search, summarize_results
import lightkurve as lk
import matplotlib.pyplot as plt
from pipeline import load_lightcurve, iterative_tls_search, summarize_results, fetch_stellar_mass, make_planet_schematic
from astroquery.mast import Observations, Mast
# Log out to clear any stale auth/session
try:
    Mast.logout()
except Exception:
    pass

# Force the current portal endpoints explicitly (runtime hot-patch)
Observations.MAST_REQUEST_URL  = "https://mast.stsci.edu/api/v0/invoke"
Observations.MAST_DOWNLOAD_URL = "https://mast.stsci.edu/api/v0.1/Download/file"


st.set_page_config(page_title="Exoplanet Explorer", layout="wide")
st.title("🔭 Exoplanet Explorer")
st.markdown("### 🔭 Search Public Star Catalogs (MAST)")

query = st.text_input("Search for a star (e.g. 'Kepler-11', 'TIC 123456789', 'KIC 6541920')")

if query:
    with st.spinner("Searching MAST catalog..."):
        mission = st.selectbox("Mission", ["Any","Kepler","K2","TESS"], index=0)
        try:
            if mission == "Any":
                search_results = lk.search_lightcurve(query)
            else:
                search_results = lk.search_lightcurve(query, mission=mission)
        except requests.HTTPError as e:
            st.error("MAST search failed (HTTP error). This is usually a temporary portal issue or a version mismatch. "
                     "Try updating astroquery/lightkurve and retry. Details: " + str(e))
            st.stop()
        except Exception as e:
            st.error(f"MAST search failed: {e}")
            st.stop()

    if len(search_results) == 0:
        st.warning("No results found.")
    else:
        options = [f"{r.mission}: {r.target_name}" for r in search_results]
        selected = st.selectbox("Select a result:", options)

        if st.button("📥 Download and process light curve"):
            idx = options.index(selected)
            lc = search_results[idx].download().remove_nans().flatten()
            st.session_state["star_lc"] = lc
            lc.plot()
            st.pyplot()

        if "star_lc" in st.session_state:
            st.markdown("### 🛠 TLS Detection Parameters")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                period_min = st.number_input("Min Period (days)", min_value=0.1, value=1.0, step=0.1)
            with col2:
                period_max = st.number_input("Max Period (days)", min_value=period_min + 1, value=150.0, step=1.0)
            with col3:
                min_sde = st.number_input("Min SDE", min_value=1.0, value=5.0, step=0.5)
            with col4:
                max_planets = int(st.number_input("Maximum number of planets", min_value=1, value=5, step=1))

            if st.button("🔍 Run TLS on this star"):
                with st.spinner("Detecting transits..."):
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    def update_progress(i, total):
                        progress_bar.progress((i + 1) / total)
                        status_text.text(f"🔍 Searching for planet {i+1} of {total}...")

                    results = iterative_tls_search(
    st.session_state["star_lc"],
    max_planets=max_planets,
    min_snr=min_sde,
    period_min=period_min,
    period_max=period_max,
    progress_callback=update_progress
)
                    progress_bar.empty()
                    status_text.empty()


                if results:
                    st.success(f"Found {len(results)} planets")
                    summary = summarize_results(results)
                    st.table(summary)

    # Try to get stellar mass from MAST using the selected target name
                    try:
        # The selected label looks like "Kepler: Kepler-11" — we want the actual target name
                        selected_target_name = search_results[options.index(selected)].target_name
                        m_star = fetch_stellar_mass(selected_target_name)
                    except Exception:
                        m_star = 1.0  # fallback if not found

                   
                    st.markdown("#### 🛰 System sketch (distances only, radii not to scale)")
                    m_star_guess = st.number_input("Stellar mass [M☉] (guess if unknown)", min_value=0.05, value=1.0, step=0.05)
                    fig = make_planet_schematic(results, star_mass=m_star)
                    st.pyplot(fig)

                else:
                    st.warning("No planets found.")

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

