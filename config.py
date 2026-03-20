# ---------------------------------------------------------------------------
# TRMNL Surf Plugin — Configuration
# ---------------------------------------------------------------------------
# Edit this file with your own stations, API keys, and preferences.
# See README.md for help finding your buoy IDs, tide station, etc.
# ---------------------------------------------------------------------------

# Your TRMNL webhook URL (found in your Private Plugin settings)
WEBHOOK_URL = "https://usetrmnl.com/api/custom_plugins/YOUR_PLUGIN_ID_HERE"

# ---------------------------------------------------------------------------
# NDBC Buoy Stations
# ---------------------------------------------------------------------------
# Each entry is (buoy_id, variable_name).
# Find buoys near you: https://www.ndbc.noaa.gov/
# Click a buoy on the map and grab the 5-character station ID.
#
# variable_name is used in the TRMNL Liquid template to reference the data.
# If you change these names, update your Liquid markup to match.
# You can use 1–4 buoys. The Liquid template expects exactly 4.

STATIONS = [
    ("46218", "harvest"),   # Harvest
    ("46025", "sm_basin"),  # Santa Monica Basin
    ("46221", "sm_bay"),    # Santa Monica Bay
    ("46268", "topanga"),   # Topanga Near Shore
]

# ---------------------------------------------------------------------------
# NOAA Tide Station
# ---------------------------------------------------------------------------
# Find your station: https://tidesandcurrents.noaa.gov/stations.html
# Search by location, then grab the 7-digit station ID from the URL.
# Example: Santa Monica is 9410840

TIDE_STATION = "9410840"
TIDE_LABEL = "Santa Monica"
TIDE_EVENTS_TO_SHOW = 6  # max 4 will display due to screen space

# ---------------------------------------------------------------------------
# Wind Station (optional)
# ---------------------------------------------------------------------------
# If you have a WeatherFlow Tempest personal weather station, enter your
# API token and station ID below. If not, set TEMPEST_TOKEN to None and
# the plugin will skip wind data.
#
# To get a Tempest API token:
#   1. Go to https://tempestwx.com/settings/tokens
#   2. Create a personal access token
#
# To find your station ID:
#   1. Go to https://tempestwx.com/station/YOUR_STATION
#   2. The numeric ID is in the URL
#
# If you don't have a Tempest, you can leave these as None.
# A future version may support NOAA/NWS wind stations.

TEMPEST_TOKEN = None        # e.g. "abc123-your-token-here"
TEMPEST_STATION_ID = None   # e.g. 123456
