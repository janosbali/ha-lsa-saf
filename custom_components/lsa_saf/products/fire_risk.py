"""Fire Risk Map v3 (FRMv3) product metadata.

The public WMS provides daily Europe-wide forecasts for day 0 through day 9.
A Home Assistant point-sampling implementation is intentionally not enabled in
v0.1.0 until the WMS GetFeatureInfo response contract is verified against live data.
"""
PRODUCT_ID = "FRMv3"
LSA_ID = "LSA-504.3"
WMS_DATASET = "MSG-FRMv3"
UPDATE_SCHEDULE_UTC = "08:30"
FORECAST_DAYS = 10
STATUS = "planned"
