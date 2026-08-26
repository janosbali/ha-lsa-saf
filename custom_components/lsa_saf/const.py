"""Constants for the LSA SAF integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "lsa_saf"
NAME = "LSA SAF"
MANUFACTURER = "EUMETSAT / LSA SAF"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_PRODUCTS = "products"
CONF_RADIUS_KM = "radius_km"
CONF_MIN_CONFIDENCE = "min_confidence"
CONF_MIN_FRP_MW = "min_frp_mw"
CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"
CONF_DEDUP_RADIUS_KM = "dedup_radius_km"
CONF_DEDUP_HOURS = "dedup_hours"
CONF_RESOLVE_PLACE_NAMES = "resolve_place_names"

PRODUCT_ACTIVE_FIRE = "active_fire"
PRODUCT_FIRE_RISK = "fire_risk"
PRODUCT_LAND_SURFACE_TEMPERATURE = "land_surface_temperature"

SUPPORTED_PRODUCTS = (PRODUCT_ACTIVE_FIRE,)
PLANNED_PRODUCTS = (PRODUCT_FIRE_RISK, PRODUCT_LAND_SURFACE_TEMPERATURE)

DEFAULT_PRODUCTS = [PRODUCT_ACTIVE_FIRE]
DEFAULT_RADIUS_KM = 25.0
DEFAULT_MIN_CONFIDENCE = 0.0
DEFAULT_MIN_FRP_MW = 0.0
DEFAULT_SCAN_INTERVAL_MINUTES = 5
DEFAULT_DEDUP_RADIUS_KM = 3.0
DEFAULT_DEDUP_HOURS = 6
DEFAULT_RESOLVE_PLACE_NAMES = False
MIN_RADIUS_KM = 1.0
MAX_RADIUS_KM = 500.0
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES)

PLATFORMS = ["sensor", "event", "number", "geo_location"]

EVENT_NEW_FIRE = "new_fire"
BUS_EVENT_NEW_FIRE = f"{DOMAIN}_new_fire"

ATTR_DISTANCE_KM = "distance_km"
ATTR_LATITUDE = "latitude"
ATTR_LONGITUDE = "longitude"
ATTR_FRP_MW = "frp_mw"
ATTR_CONFIDENCE = "confidence"
ATTR_ACQUIRED = "acquired"
ATTR_PIXEL_COUNT = "pixel_count"
ATTR_TRACK_ID = "track_id"
ATTR_SOURCE_URL = "source_url"
ATTR_PRODUCT_TIME = "product_time"
ATTR_PEAK_FRP_MW = "peak_frp_mw"
ATTR_PLACE_NAME = "place_name"
ATTR_NEAREST_SETTLEMENT = "nearest_settlement"
ATTR_LOCATION_DESCRIPTION = "location_description"
ATTR_PLACE_ATTRIBUTION = "place_attribution"
