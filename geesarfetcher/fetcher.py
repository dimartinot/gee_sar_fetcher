from geesarfetcher.filter import filter_sentinel1_data
from geesarfetcher.constants import VV, VH, IW, ASCENDING

__all__ = ["fetch_sentinel1_data"]

def fetch_sentinel1_data(start_date, end_date, geometry, scale, orbit=ASCENDING):
    """
    """
    sentinel_1_roi = filter_sentinel1_data(
            start_date=start_date,
            end_date=end_date,
            geometry=geometry,
            orbit=orbit
    )
    val_vv = (sentinel_1_roi
              .select(VV)
              .getRegion(geometry, scale=scale)
              .getInfo()
    )
    val_vh = (sentinel_1_roi
              .select(VH)
              .getRegion(geometry, scale=scale)
              .getInfo()
    )
    val_header = val_vv[0][1:] + [VH]
    val = [
            val_vv[i][1:] + [val_vh[i][val_vh[0].index(VH)]] for i in range(1, len(val_vv))
    ]
    return (val_header, val)
