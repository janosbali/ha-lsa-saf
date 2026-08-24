"""MTG Land Surface Temperature (MTLST / LSA-007) product metadata.

MTLST is a 2 km / 10 minute pre-operational NetCDF4 product. Point extraction
will be added after the live NetCDF coordinate/grid mapping is validated on the
same hardware Home Assistant uses.
"""
PRODUCT_ID = "MTLST"
LSA_ID = "LSA-007"
DATA_PATH = "MTG/MTLST"
TEMPORAL_RESOLUTION_MINUTES = 10
SPATIAL_RESOLUTION_KM = 2
STATUS = "planned"
