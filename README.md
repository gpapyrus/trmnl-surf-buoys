# TRMNL Surf Plugin

A custom TRMNL plugin that displays real-time surf conditions on your e-ink display: wave height, period, direction, and water temp from up to 4 NDBC buoys, plus tide predictions and optional local wind data.

If you're technologically inclined, this should be pretty straightforward. If you're not, you can throw this text into one of the AI systems and it should be able to walk you through everything step-by-step. 

## What It Shows

- **4 buoy readings** — current, previous, and 24-hours-ago wave conditions
- **Tide predictions** — next upcoming high/low tides for your local station
- **Wind data** (optional) — from a WeatherFlow Tempest personal weather station
- **Swell window** (optional) — customizable line for your local break

## Requirements

- A [TRMNL](https://usetrmnl.com) device
- Python 3.7+ (standard library only — no pip installs needed)
- A computer that stays on to run the script on a schedule (Raspberry Pi, home server, always-on laptop, etc.)

## Quick Start

### 1. Create a TRMNL Private Plugin

1. Log into [trmnl.com](https://trmnl.com) and go to **Plugins > Private Plugin**
2. You'll get a webhook URL — copy it for the next step
3. Leave the Markup editor open; you'll paste templates in Step 4

### 2. Download and Configure

Copy the project files to your machine:

```
trmnl-surf/
  config.py         ← your personal settings (edit this)
  trmnl_surf.py     ← the main script (don't edit)
  templates.liquid   ← Liquid templates for TRMNL (reference)
  README.md          ← this file
```

Open `config.py` and fill in your settings:

```python
WEBHOOK_URL = "https://usetrmnl.com/api/custom_plugins/YOUR_PLUGIN_ID_HERE"
```

### 3. Choose Your Stations

#### Finding NDBC Buoy IDs

1. Go to [ndbc.noaa.gov](https://www.ndbc.noaa.gov/)
2. Use the map to find buoys near your surf spots
3. Click a buoy — the station ID is the 5-character code (e.g., `46221`)
4. Look for buoys that report wave data (WVHT, DPD, MWD columns)
5. Add up to 4 buoys to `config.py`:

```python
STATIONS = [
    ("46221", "buoy_1"),   # Give each a short, unique variable name
    ("46025", "buoy_2"),
    ("46253", "buoy_3"),
    ("46268", "buoy_4"),
]
```

#### Finding Your NOAA Tide Station

1. Go to [tidesandcurrents.noaa.gov/stations.html](https://tidesandcurrents.noaa.gov/stations.html)
2. Search for a station near your surf spot
3. Click it — the 7-digit station ID is in the URL
4. Update `config.py`:

```python
TIDE_STATION = "9410840"      # e.g., Santa Monica
TIDE_LABEL = "Santa Monica"   # display name (not shown on device currently)
```

#### Wind Station (Optional)

If you have a [WeatherFlow Tempest](https://weatherflow.com/tempest-weather-system/) personal weather station:

1. Get an API token at [tempestwx.com/settings/tokens](https://tempestwx.com/settings/tokens)
2. Find your station ID in your Tempest station URL
3. Update `config.py`:

```python
TEMPEST_TOKEN = "your-token-here"
TEMPEST_STATION_ID = 123456
```

If you don't have a Tempest, leave both as `None`. The wind line will simply not appear on the display.

### 4. Set Up the TRMNL Templates

Open `templates.liquid` for reference, then:

1. **Shared section** — Copy the `buoy_card` template (everything between `{% template buoy_card %}` and `{% endtemplate %}`) into your plugin's Shared markup area
2. **Main markup** — Copy the main markup section into your plugin's Markup area
3. **Update buoy names** — Change the `title:` values and variable names in the `{% render %}` calls to match what you put in `config.py`

For example, if your config has:

```python
STATIONS = [
    ("46221", "local_buoy"),
    ...
]
```

Then your render call should be:

```liquid
{% render "buoy_card", obj: local_buoy, prev: local_buoy_prev, ago: local_buoy_24h, title: "My Buoy (46221)" %}
```

#### Optional: Swell Window

If you know the swell window for your local break, uncomment the swell window section in the main markup and fill in your angles. You can calculate your swell window using the maps at [stormsurf.com](https://stormsurf.com).

### 5. Test It

Run the script manually:

```bash
cd /path/to/trmnl-surf
python3 trmnl_surf.py
```

You should see output like:

```
2026-03-20 12:00:00 Posted 4/4 buoys + tide + wind to TRMNL.
```

Check your TRMNL plugin editor — the preview should update with live data.

### 6. Set Up Automated Updates

The script needs to run on a schedule. A cron job every 10 minutes works well — NDBC buoys update roughly every 30 minutes, but running more frequently ensures you catch updates quickly.

#### On a Raspberry Pi or Linux Server

```bash
crontab -e
```

Add this line (adjust the path to where you put the files):

```
*/10 * * * * cd /home/YOUR_USER/trmnl-surf && /usr/bin/python3 trmnl_surf.py >> /home/YOUR_USER/trmnl-surf/trmnl.log 2>&1
```

This runs every 10 minutes and logs output to `trmnl.log`.

#### On a Mac (launchd)

Create `~/Library/LaunchAgents/com.trmnl.surf.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.trmnl.surf</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/trmnl-surf/trmnl_surf.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/trmnl-surf</string>
    <key>StartInterval</key>
    <integer>600</integer>
    <key>StandardOutPath</key>
    <string>/path/to/trmnl-surf/trmnl.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/trmnl-surf/trmnl.log</string>
</dict>
</plist>
```

Then load it:

```bash
launchctl load ~/Library/LaunchAgents/com.trmnl.surf.plist
```

### 7. Set Your TRMNL Refresh Rate

In your TRMNL device settings ([trmnl.com/devices](https://trmnl.com/devices) > Edit), set the refresh interval. Every 15 minutes makes sense to catch the most recent updates.

## Troubleshooting

**"No recent data" on a buoy card:**
That buoy may be offline or not reporting wave data. Check [ndbc.noaa.gov](https://www.ndbc.noaa.gov/) to see if the buoy is active.

**Wind line not showing:**
Make sure `TEMPEST_TOKEN` and `TEMPEST_STATION_ID` are set in `config.py`. If both are `None`, the wind line is intentionally hidden.

**Tide data missing:**
Verify your tide station ID at [tidesandcurrents.noaa.gov](https://tidesandcurrents.noaa.gov). Some stations only have water level data, not predictions.

## Data Sources

- **Wave data:** [NOAA National Data Buoy Center (NDBC)](https://www.ndbc.noaa.gov/) — public, no API key needed
- **Tide predictions:** [NOAA CO-OPS Tides & Currents](https://tidesandcurrents.noaa.gov/) — public, no API key needed
- **Wind data:** [WeatherFlow Tempest](https://weatherflow.com/) — requires personal weather station + API token

## License

MIT — do whatever you want with it. If you build something cool, share it with the TRMNL community.
