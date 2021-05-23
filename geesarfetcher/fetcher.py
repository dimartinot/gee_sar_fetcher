from geesarfetcher.filter import filter_sentinel1_data
from geesarfetcher.constants import VV, VH, IW, ASCENDING, GEE_PROPERTIES

__all__ = ["fetch_sentinel1_data", "fetch_sentinel1_properties"]


def fetch_sentinel1_data(
    start_date, end_date, geometry, scale, orbit=ASCENDING, orbit_number=None
):
    """
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
    orbit_number : int or str, optional
        The orbit number to restrict the download to. If provided with an integer, the S1 temporal stack is filtered using the provided orbit number.
        If provided with a string value, we expect one of these keywords:
         - "max" for the orbit number with the highest number of image in the stack
         - "min" for the orbit number with the smallest number of image in the stack
        If ``None``, then no filter over the orbit number is applied.

    Returns
    -------
    `dict`
        Returns a dictionnary of the properties of the Image retrieved from GEE.

    """
    sentinel_1_roi = filter_sentinel1_data(
        start_date=start_date,
        end_date=end_date,
        geometry=geometry,
        orbit=orbit,
        orbit_number=orbit_number,
    )
    val_vv = sentinel_1_roi.select(VV).getRegion(geometry, scale=scale).getInfo()
    val_vh = sentinel_1_roi.select(VH).getRegion(geometry, scale=scale).getInfo()
    val_header = val_vv[0][1:] + [VH]
    val = [
        val_vv[i][1:] + [val_vh[i][val_vh[0].index(VH)]] for i in range(1, len(val_vv))
    ]
    return (val_header, val)


def fetch_sentinel1_properties(
    start_date, end_date, geometry, orbit=ASCENDING, orbit_number=None
):
    """
    Retrieves and queries ImageCollection using input parameters and return Image properties.

    Parameters
    ----------
    start_date : str
        str following the pattern ``'yyyy-mm-dd'`` describing the start date of the time interval
    end_date : str
        str following the pattern ``'yyyy-mm-dd'`` describing the end date of the time interval
    geometry : ee.Geometry
        Geometry object defining the area of process
    orbit : str, optional
        Defines the orbit to set for the data retrieval process
    orbit_number : int or str, optional
        The orbit number to restrict the download to. If provided with an integer, the S1 temporal stack is filtered using the provided orbit number.
        If provided with a string value, we expect one of these keywords:
         - "max" for the orbit number with the highest number of image in the stack
         - "min" for the orbit number with the smallest number of image in the stack
        If ``None``, then no filter over the orbit number is applied.

    Returns
    -------
     : tuple
        val_header corresponds to the ``list of str`` describing the fields of the val array. The val array is a ``list`` of data records, each represented as a ``list`` of the same size as the val_header array.

    """
    sentinel_1_roi = filter_sentinel1_data(
        start_date=start_date,
        end_date=end_date,
        geometry=geometry,
        orbit=orbit,
        orbit_number=orbit_number,
    )
    properties_dict = {}
    for i in range(len(GEE_PROPERTIES)):
        try:
            key = GEE_PROPERTIES[i]
            value = sentinel_1_roi.first().get(key).getInfo()
            properties_dict[key] = value
        except Exception as e:
            return None
            pass
    return properties_dict


def _get_zone_between_dates(
    start_date, end_date, polygon, scale, orbit, orbit_number, headers
):
    try:
        val_header, val = fetch_sentinel1_data(
            start_date=start_date,
            end_date=end_date,
            geometry=polygon,
            orbit=orbit,
            orbit_number=orbit_number,
            scale=scale,
        )

        if len(headers) == 0:
            headers.extend(val_header)

        return val

    except Exception as e:
        pass


def _get_properties_between_dates(start_date, end_date, polygon, orbit, orbit_number):
    try:
        dict = fetch_sentinel1_properties(
            start_date=start_date,
            end_date=end_date,
            geometry=polygon,
            orbit=orbit,
            orbit_number=orbit_number,
        )

        return dict

    except Exception as e:
        pass