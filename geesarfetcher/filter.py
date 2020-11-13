from geesarfetcher.constants import SENTINEL1_COLLECTION_ID
from geesarfetcher.constants import VV, VH, IW
import ee

def filter_sentinel1_data(start_date, end_date, geometry, orbit='ASCENDING'):
    """Filters Sentinel-1 products to get images collected in interferometric
    wide swath mode (IW) and on i) a date range, ii) a geometry and iii)
    ascending or descending orbit.
    """
    filtered_data = (ee.ImageCollection(SENTINEL1_COLLECTION_ID)
                      .filter(ee.Filter.date(start_date, end_date))
                      .filterBounds(geometry)
                      .filter(ee.Filter.listContains('transmitterReceiverPolarisation', VV))
                      .filter(ee.Filter.listContains('transmitterReceiverPolarisation', VH))
                      .filter(ee.Filter.eq('instrumentMode', IW))
                      .filter(ee.Filter.eq('orbitProperties_pass', orbit))
                      .filter(ee.Filter.eq('resolution_meters', 10))
    )
    return filtered_data
