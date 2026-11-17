"""Forecast GTA VI's launch-day Twitch viewers hour by hour.

Model (fit from the case's own comparables, nothing else):

Launch days have a shape. Hour 1 of the UTC release day anchors the level:
how much of the launch had already happened by 01:00 UTC. Across past big
launches, the rest of the day's curve, in log space relative to hour 1,
depends strongly on that anchor: a launch that was already huge at hour 1
stays comparatively flat (the world was already watching), while a launch
that was still small at hour 1 surges later (its audience arrives through
the day). The log-ratio of each later hour to hour 1 is almost linear in
log(hour-1 viewers), with a slope that grows more negative through the day
(about +0.05 at hour 2 to about -0.36 at hour 21).

So for each hour h = 2..24 this program fits, over the peer launches in the
case, an ordinary least-squares line

    ln(viewers_h / viewers_1)  =  a_h + b_h * ln(viewers_1)

then forecasts GTA VI's hour h from its own hour-1 print. The fitted
intercepts and slopes are smoothed across neighbouring hours (3-hour
centred moving average) because the true shape moves smoothly through the
day. Outside the peer launches' hour-1 range the line is extrapolated at
half slope, and the spread is widened in proportion to the distance, so a
launch bigger than anything seen before is forecast cautiously, not wildly.

Peers are the case's comparables that look like this launch: their hour-1
print is at least 15% of their release-day peak (so hour 1 was a real
launch hour, not the quiet before a later global unlock), they are not
flagged early-access-contaminated, and they are not the GTA VI category
itself. The spread around the centre comes mostly from the empirical
quantiles of the fit's residuals at that hour (which are asymmetric: the
downside tail is fatter), blended with a normal random-walk spread that
widens with the square root of the hours since hour 1.

Everything is deterministic: no randomness, no clock, no network, standard
library only. One run reads every *.in file in the input directory and
writes one *.out per case.

Usage (as the grader runs it):
    python3 main.py
with MAKEFUN_INPUT_DIR / MAKEFUN_OUTPUT_DIR standing in for /input and
/output outside the grader's container.
"""

import json
import math
import os
import sys
from pathlib import Path

# The grader runs with -P, which leaves this file's directory off sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]

# How much of the spread comes from the empirical residual quantiles
# (the rest is the normal random-walk component).
EMPIRICAL_BLEND = 0.7
# Normal spread, in log units per square-root hour.
SIGMA = 0.13
# Slope kept when extrapolating beyond the peers' hour-1 range.
DAMP = 0.5
# Extra log-spread per log-unit of extrapolation beyond the peer range.
EXTRA_SPREAD = 0.10
# A peer's hour 1 must be at least this share of its release-day peak.
PEER_MIN_H1_SHARE = 0.15


def round2(x):
    """Round to 2 decimals, half up, returning an int for whole numbers."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value == int(value) else value


def release_day_hours(comp):
    """Hour -> viewers for the comparable's release day (hours 1..24)."""
    day = comp["day_start"][:10]
    out = {}
    for row in comp.get("hourly", []):
        if row["from"][:10] == day:
            out[int(row["from"][11:13]) + 1] = row["viewers"]
    return out


def is_peer(comp):
    """Is this comparable a launch whose day-1 shape informs GTA VI?"""
    name = comp.get("name", "")
    if "Grand Theft Auto VI" in name:
        return False
    if "early-access-contaminated" in comp.get("unlock", ""):
        return False
    series = release_day_hours(comp)
    if 1 not in series:
        return False
    peak = max(series.values())
    return peak > 0 and series[1] >= PEER_MIN_H1_SHARE * peak


def ols(xs, ys):
    """Least-squares line y = a + b*x; returns (a, b)."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return my, 0.0
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return my - b * mx, b


def smooth3(values):
    """Centred 3-hour moving average over the hours present in values."""
    out = {}
    for h, v in values.items():
        near = [values[hh] for hh in (h - 1, h, h + 1) if hh in values]
        out[h] = sum(near) / len(near)
    return out


def fit_shape(comparables):
    """Fit the per-hour log-ratio lines over the peer launches.

    Returns (peers, fits) where peers is a list of (log h1, {hour: log-ratio})
    and fits maps hour -> (a, b, residuals sorted, xmin, xmax).
    """
    peers = []
    for comp in comparables:
        if not is_peer(comp):
            continue
        series = release_day_hours(comp)
        h1 = series[1]
        if h1 < 1:
            continue
        curve = {}
        for h in range(2, 25):
            if h in series and series[h] >= 1:
                curve[h] = math.log(series[h] / h1)
        if curve:
            peers.append((math.log(h1), curve))
    fits = {}
    for h in range(2, 25):
        pts = [(x, c[h]) for x, c in peers if h in c]
        if len(pts) < 4:
            continue
        a, b = ols([p[0] for p in pts], [p[1] for p in pts])
        resid = sorted(y - (a + b * x) for x, y in pts)
        fits[h] = (a, b, resid, min(p[0] for p in pts), max(p[0] for p in pts))
    # The shape moves smoothly through the day: smooth intercepts and slopes.
    if fits:
        a_s = smooth3({h: f[0] for h, f in fits.items()})
        b_s = smooth3({h: f[1] for h, f in fits.items()})
        for h in fits:
            a, b, resid, xmin, xmax = fits[h]
            fits[h] = (a_s[h], b_s[h], resid, xmin, xmax)
    return peers, fits


def hour_quantiles(p1, h, fits):
    """Five quantiles of hour h's viewers, given hour-1 print p1."""
    log_p1 = math.log(max(1.0, p1))
    if h not in fits:
        # No peer line for this hour: fall back to the house persistence
        # forecast (flat at hour 1, spread widening over the day).
        return [round2(max(1.0, p1) * math.exp(z * 0.15 * math.sqrt(h - 1)))
                for z in Z]
    a, b, resid, xmin, xmax = fits[h]
    if log_p1 > xmax:
        x_eff = xmax + DAMP * (log_p1 - xmax)
        x_dist = log_p1 - xmax
    elif log_p1 < xmin:
        x_eff = xmin + DAMP * (log_p1 - xmin)
        x_dist = xmin - log_p1
    else:
        x_eff, x_dist = log_p1, 0.0
    centre = a + b * x_eff
    n = len(resid)
    emp = [resid[min(n - 1, int(t * (n - 1)))] for t in LEVELS]
    sigma = SIGMA * math.sqrt(h - 1) + EXTRA_SPREAD * min(x_dist, 3.0)
    norm = [z * sigma for z in Z]
    qs = []
    prev = 0.0
    for e, s in zip(emp, norm):
        q = max(1.0, p1 * math.exp(centre + EMPIRICAL_BLEND * e + (1.0 - EMPIRICAL_BLEND) * s))
        q = min(q, 1e9)
        q = max(q, prev)  # keep the row non-decreasing
        prev = q
        qs.append(round2(q))
    return qs


def forecast_case(case, name):
    """Forecast one case: 23 rows, hours 2..24, five quantiles each."""
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(name + " has no hour-1 print")
    p1 = max(1.0, float(first["viewers"]))
    _, fits = fit_shape(case.get("comparables", []))
    rows = []
    for row in case["forecast"]:
        h = row["hour"]
        rows.append({"hour": h, "q": hour_quantiles(p1, h, fits)})
    return {"hours": rows}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        text = json.dumps(forecast, separators=(",", ":")) + "\n"
        (OUTPUT_DIR / (path.stem + ".out")).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
