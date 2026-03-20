#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# TRMNL Surf Plugin
# ---------------------------------------------------------------------------
# Posts latest, previous, and 24h-ago wave records for NDBC buoys,
# a compact tide list, and optional Tempest wind data to a TRMNL
# private plugin via webhook.
#
# Standard library only — no pip installs required.
#
# Usage:
#   1. Edit config.py with your stations and API keys
#   2. Run: python3 trmnl_surf.py
#   3. Set up a cron job to run every 10–15 minutes (see README.md)
# ---------------------------------------------------------------------------

import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta

from config import (
    WEBHOOK_URL,
    STATIONS,
    TIDE_STATION,
    TIDE_LABEL,
    TIDE_EVENTS_TO_SHOW,
    TEMPEST_TOKEN,
    TEMPEST_STATION_ID,
)

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _is_number(x):
    return isinstance(x, (int, float)) and not (x != x)

def _ft(m):
    return round(m * 3.281, 1) if _is_number(m) else None

def _mph(ms):
    return round(ms * 2.237) if _is_number(ms) else None

def _f(c):
    return round((c * 9 / 5) + 32) if _is_number(c) else None

def deg_to_cardinal(deg):
    """16-point compass from degrees; returns None if deg is None."""
    if deg is None:
        return None
    dirs = ['N',  'NNE', 'NE', 'ENE', 'E',  'ESE', 'SE', 'SSE',
            'S',  'SSW', 'SW', 'WSW', 'W',  'WNW', 'NW', 'NNW']
    idx = int(((float(deg) % 360) / 22.5) + 0.5) % 16
    return dirs[idx]

def iso_to_local_str(iso_s):
    """Convert ISO8601 '...Z' to local time string like '10/27 5:56 PM'."""
    if not iso_s:
        return None
    dt_utc = datetime.fromisoformat(iso_s.replace("Z", "+00:00"))
    dt_local = dt_utc.astimezone()
    return dt_local.strftime("%-m/%-d %-I:%M %p")

def iso_to_local_date(iso_s):
    """Convert ISO8601 '...Z' to local date string like '3/20'."""
    if not iso_s:
        return None
    dt_utc = datetime.fromisoformat(iso_s.replace("Z", "+00:00"))
    dt_local = dt_utc.astimezone()
    return dt_local.strftime("%-m/%-d")

def iso_to_local_time(iso_s):
    """Convert ISO8601 '...Z' to local time string like '8:56 AM'."""
    if not iso_s:
        return None
    dt_utc = datetime.fromisoformat(iso_s.replace("Z", "+00:00"))
    dt_local = dt_utc.astimezone()
    return dt_local.strftime("%-I:%M %p")

def _is_valid_wave(rec):
    """Require wvht, dpd, and mwd to all be positive."""
    return (
        _is_number(rec.get("wvht")) and rec["wvht"] > 0
        and _is_number(rec.get("dpd")) and rec["dpd"] > 0
        and _is_number(rec.get("mwd")) and rec["mwd"] > 0
    )

def normalize(rec):
    """Compact dict for TRMNL: h(ft), p(s), d(deg), dc(cardinal), w(F), t/td/tt(time)."""
    if not rec:
        return None
    def I(x): return int(x) if _is_number(x) else None
    d = I(rec.get("mwd"))
    return {
        "h": _ft(rec.get("wvht")),
        "p": I(rec.get("dpd")),
        "d": d,
        "dc": deg_to_cardinal(d),
        "w": _f(rec.get("wtmp")),
        "t": iso_to_local_str(rec.get("time")),
        "td": iso_to_local_date(rec.get("time")),
        "tt": iso_to_local_time(rec.get("time")),
    }

# ---------------------------------------------------------------------------
# NDBC buoy data
# ---------------------------------------------------------------------------

def fetch_pair_from_ndbc_txt(station_id):
    """
    Parse NDBC realtime2 station file.
    Returns (cur, prev, ago_24h) where each is a dict or None.
    Newest rows are first; we grab the first two valid records,
    plus the record closest to 24 hours before the current reading.
    """
    url = f"https://www.ndbc.noaa.gov/data/realtime2/{station_id}.txt"
    with urllib.request.urlopen(url, timeout=20) as resp:
        lines = resp.read().decode("utf-8", "ignore").strip().splitlines()

    header = None
    data_lines = []
    for ln in lines:
        if ln.startswith("#"):
            tokens = ln.replace("#", "").split()
            if ("YY" in tokens or "YYYY" in tokens) and "WVHT" in tokens:
                header = tokens
        elif ln.strip():
            data_lines.append(ln.split())

    if not header or not data_lines:
        return None, None, None

    def idx(name, default=None):
        return header.index(name) if name in header else default

    iY = idx("YYYY", idx("YY"))
    iM, iD, ih, im = idx("MM"), idx("DD"), idx("hh"), idx("mm")
    iWVHT, iDPD, iMWD = idx("WVHT"), idx("DPD"), idx("MWD")
    iWTMP = idx("WTMP")

    bad_tokens = {"MM", "99", "99.0", "99.00", "999", "999.0", "999.00"}

    def val(tokens, i):
        if i is None or i >= len(tokens):
            return None
        s = tokens[i]
        if s in bad_tokens:
            return None
        try:
            return float(s)
        except Exception:
            return None

    def row_to_rec(tokens):
        try:
            Y = int(tokens[iY])
            Y = (2000 + Y) if Y < 100 else Y
            M, D, h, m = int(tokens[iM]), int(tokens[iD]), int(tokens[ih]), int(tokens[im])
            dt = datetime(Y, M, D, h, m)
            rec = {
                "station": station_id,
                "time": dt.strftime("%Y-%m-%dT%H:%M:00Z"),
                "wvht": val(tokens, iWVHT),
                "dpd": val(tokens, iDPD),
                "mwd": val(tokens, iMWD),
                "wtmp": val(tokens, iWTMP),
            }
            return rec if _is_valid_wave(rec) else None
        except Exception:
            return None

    cur = prev = ago_24h = None
    for tokens in data_lines:
        rec = row_to_rec(tokens)
        if rec:
            if cur is None:
                cur = rec
            elif prev is None:
                prev = rec

    # Find the record closest to 24 hours before the current reading
    if cur:
        cur_dt = datetime.fromisoformat(cur["time"].replace("Z", "+00:00"))
        target = cur_dt - timedelta(hours=24)
        best_diff = None
        for tokens in data_lines:
            rec = row_to_rec(tokens)
            if rec:
                rec_dt = datetime.fromisoformat(rec["time"].replace("Z", "+00:00"))
                diff = abs((rec_dt - target).total_seconds())
                if best_diff is None or diff < best_diff:
                    best_diff = diff
                    ago_24h = rec

    return cur, prev, ago_24h

def fetch_current_and_prev_valid(station_id):
    """Fetch current, previous, and 24h-ago wave records from NDBC."""
    return fetch_pair_from_ndbc_txt(station_id)

# ---------------------------------------------------------------------------
# Tides (NOAA CO-OPS)
# ---------------------------------------------------------------------------

def fetch_tide_events(station, label, events_to_show):
    """Next N high/low events as compact dicts."""
    now_local = datetime.now().astimezone()
    local_tz = now_local.tzinfo
    today = now_local.date()
    tomorrow = (now_local + timedelta(days=1)).date()

    url = (
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        f"?product=predictions&application=trmnl"
        f"&format=json&datum=MLLW&time_zone=lst_ldt&units=english"
        f"&interval=hilo&station={station}"
        f"&begin_date={today.strftime('%Y%m%d')}"
        f"&end_date={tomorrow.strftime('%Y%m%d')}"
    )
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            js = json.load(resp)
        out = []
        for p in js.get("predictions", []):
            dt = datetime.strptime(p["t"], "%Y-%m-%d %H:%M").replace(tzinfo=local_tz)
            if dt < now_local:
                continue
            out.append({
                "k": p["type"],
                "t": dt.strftime("%-I:%M %p").lstrip("0"),
                "v": round(float(p["v"]), 1),
            })
            if len(out) >= min(events_to_show, 4):
                break
        return {"label": label, "e": out}
    except Exception as e:
        return {"label": label, "error": f"Tide fetch error: {e}"}

# ---------------------------------------------------------------------------
# Tempest wind (WeatherFlow) — optional
# ---------------------------------------------------------------------------

def fetch_tempest_wind(token, station_id):
    """Return compact wind dict or {'_err': ...}. Returns None if not configured."""
    if not token or not station_id:
        return None

    url = (
        "https://swd.weatherflow.com/swd/rest/observations/station"
        f"?station_id={urllib.parse.quote(str(station_id))}&units=us"
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})

    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            js = json.load(r)

        obs = js.get("obs") or js.get("observations") or []
        if not obs:
            return {"_err": "no_obs"}

        o = obs[-1]
        def num(x): return isinstance(x, (int, float)) and not (x != x)

        ts = o.get("timestamp")
        tstr = datetime.fromtimestamp(ts).astimezone().strftime("%-m/%-d %-I:%M %p") if ts else None
        sp = round(o.get("wind_avg")) if num(o.get("wind_avg")) else None
        gs = round(o.get("wind_gust")) if num(o.get("wind_gust")) else None

        d_raw = o.get("wind_direction") or o.get("wind_dir")
        dd = int(d_raw) if num(d_raw) else None
        dc = deg_to_cardinal(dd) if dd is not None else None

        return {"sp": sp, "gs": gs, "d": dd, "dc": dc, "t": tstr}

    except Exception as e:
        return {"_err": f"{type(e).__name__}: {e}"}

# ---------------------------------------------------------------------------
# TRMNL webhook
# ---------------------------------------------------------------------------

def post_to_trmnl(merge):
    """POST merge variables to the TRMNL webhook."""
    data = json.dumps({"merge_variables": merge}).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Webhook HTTP {e.code}: {body}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    merge = {}
    posted = 0

    # Buoys
    for buoy_id, key in STATIONS:
        try:
            cur, prev, ago_24h = fetch_current_and_prev_valid(buoy_id)
            if cur:
                merge[key] = normalize(cur)
                posted += 1
            if prev:
                merge[f"{key}_prev"] = normalize(prev)
            if ago_24h:
                merge[f"{key}_24h"] = normalize(ago_24h)
        except Exception as e:
            merge[f"{key}_error"] = f"{type(e).__name__}: {e}"

    # Tides
    merge["tide"] = fetch_tide_events(TIDE_STATION, TIDE_LABEL, TIDE_EVENTS_TO_SHOW)

    # Wind (optional — skipped if not configured)
    wx = fetch_tempest_wind(TEMPEST_TOKEN, TEMPEST_STATION_ID)
    if wx is not None:
        merge["wx"] = wx

    # Push to TRMNL
    if not merge:
        print(datetime.now().strftime("%F %T"), "No data fetched.")
        raise SystemExit(1)

    post_to_trmnl(merge)
    print(datetime.now().strftime("%F %T"),
          f"Posted {posted}/{len(STATIONS)} buoys + tide + wind to TRMNL.")
