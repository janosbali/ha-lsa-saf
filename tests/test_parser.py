"""Parser tests using a synthetic MTFRPPixel CSV payload."""
from datetime import UTC
import gzip

from custom_components.lsa_saf.products.fire import haversine_km, parse_product


def test_parse_product() -> None:
    csv_text = (
        "LATITUDE,LONGITUDE,FIRE_CONFIDENCE,FRP,ACQTIME,PIXEL_SIZE,FRP_UNCERTAINTY,ABS_LINE,ABS_SAMP\n"
        "46.30,20.18,0.91,12.4,20260821101030,1.2,2.1,100,200\n"
    )
    filename = "LSA-509_MTG_MTFRPPIXEL-ListProduct_MTG-FD_202608211000.csv.gz"
    product = parse_product(filename, "https://example.invalid/file", gzip.compress(csv_text.encode()))
    assert product.product_time.tzinfo == UTC
    assert len(product.pixels) == 1
    assert product.pixels[0].confidence == 0.91
    assert product.pixels[0].frp_mw == 12.4


def test_haversine() -> None:
    assert haversine_km(46.22, 20.19, 46.22, 20.19) == 0
    assert 10 < haversine_km(46.22, 20.19, 46.32, 20.19) < 12
