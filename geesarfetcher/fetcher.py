from geesarfetcher.filter import filter_sentinel1_data
from geesarfetcher.constants import VV, VH, IW, ASCENDING

__all__ = ["fetch_sentinel1_data"]

def fetch_sentinel1_data(start_date, end_date, geometry, scale, orbit=ASCENDING):
    '''
    Retrieves and queries ImageCollection using input parameters and return data as a tuple of header and values.

    Parameters
    ----------
    start_date : str
        str following the pattern ``'yyyy-mm-dd'`` describing the start date of the time interval
    end_date : str
        str following the pattern ``'yyyy-mm-dd'`` describing the end date of the time interval
    geometry : ee.Geometry
        Geometry object defining the area of process
    scale : int
        Scale parameters of the getRegion() function. Defaulting at ``20``, change it to change the scale of the final data points. The highest, the lower the spatial resolution. Should be at least ``10``.
    orbit : str, optional
        Defines the orbit to set for the data retrieval process

    Returns
    -------
    (val_header, val) : tuple
        val_header corresponds to the ``list of str`` describing the fields of the val array. The val array is a ``list`` of data records, each represented as a ``list`` of the same size as the val_header array.

    '''
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
