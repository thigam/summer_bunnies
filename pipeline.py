# pipeline.py

import numpy as np
import matplotlib.pyplot as plt
import lightkurve as lk
from transitleastsquares import transitleastsquares, transit_mask
from astropy.constants import G, R_sun, M_sun
from astroquery.mast import Catalogs
import io
import pickle

# NumPy patch
if not hasattr(np, 'int'): np.int = int
if not hasattr(np, 'float'): np.float = float


def load_lightcurve(uploaded_file):
    # Try reading with Lightkurve first
    try:
        lc = lk.read(uploaded_file).remove_nans().remove_outliers().flatten()
        return lc
    except Exception:
        raise ValueError("Could not read light curve file. Try .fits or .csv.")


def iterative_tls_search(lc, max_planets=5, min_snr=5, period_min=1, period_max=150, progress_callback=None):
    results = []
    time = lc.time.value if hasattr(lc.time, 'value') else lc.time
    flux = lc.flux.value if hasattr(lc.flux, 'value') else lc.flux
    time = np.array(time, dtype=float)
    flux = np.array(flux, dtype=float)

    for i in range(max_planets):
        if progress_callback:
            progress_callback(i, max_planets)
        model = transitleastsquares(time, flux)
        result = model.power(period_min=period_min, period_max=period_max, transit_mask=True)

        if result.SDE < min_snr:
            break
        results.append(result)
        mask = transit_mask(time, result.period, result.duration, result.T0)
        flux[mask] = 1.0  # or interpolate

    return results


def fetch_stellar_mass(star_name):
    catalog_data = Catalogs.query_object(star_name, catalog='TIC')
    if len(catalog_data) == 0:
        raise ValueError(f"No stellar data found for {star_name}")
    return float(catalog_data[0]['mass'])


def summarize_results(results, star_mass=1.0):
    summaries = []
    M_star_kg = star_mass * M_sun.value

    for i, res in enumerate(results):
        P_sec = res.period * 86400
        try:
            a_over_Rs = res.a
        except AttributeError:
            a_over_Rs = None

        rho_star = (3 * np.pi / (G.value * P_sec**2)) * (a_over_Rs**3) if a_over_Rs else 1408
        R_star_m = ((3 * M_star_kg) / (4 * np.pi * rho_star)) ** (1/3)
        R_planet_m = res.rp_rs * R_star_m
        R_planet_earth = R_planet_m / 6.371e6

        summaries.append({
            "Planet": f"Planet {i+1}",
            "Period [d]": round(res.period, 4),
            "Depth [ppm]": round(res.depth * 1e6, 2),
            "Duration [h]": round(res.duration, 3),
            "Radius [R_earth]": round(R_planet_earth, 2),
            "SDE": round(res.SDE, 2)
        })

    return summaries

