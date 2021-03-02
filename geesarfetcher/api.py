# LIBRARY IMPORTS
import ee
import warnings
from datetime import datetime, date, timedelta
from tqdm import tqdm
from functools import cmp_to_key
import numpy as np
from joblib import Parallel, delayed
import os

# LOCAL IMPORTS
from .constants import ASCENDING, DESCENDING
from .coordinates import populate_coordinates_dictionary
from .exceptions import IncorrectOrbitException
from .filter import filter_sentinel1_data
from .fetcher import fetch_sentinel1_data
from .fetcher import _get_zone_between_dates
from .utils import make_polygon
from .utils import tile_coordinates
from .utils import define_image_shape
from .utils import retrieve_max_pixel_count_from_pattern
from .utils import cmp_coords
from .utils import get_date_interval_array

def get_pixel_values(top_left=None, bottom_right=None, coords=None, start_date: datetime = date.today()-timedelta(days=365), end_date: datetime = date.today(), ascending: bool = True, scale=20, n_jobs=1):
    '''Given a list of coordinates and another of date intervals, loops over both to agglomerate GEE sar pixel values and returns a list of dictionnaries, one per coordinate, with intesities and timestamps.
    The higher loop is over coordinates and is concurrent. The lower loop is over dates and is parallelised.

    Parameters
    ----------
    top_left : tuple of float, optional
        Top left coordinates (lon, lat) of the Region 

    bottom_right : tuple of float, optional
        Bottom right coordinates (lon, lat) of the Region

    coords : tuple of tuple of float or list of list of float, optional
        If `top_left` and `bottom_right` are not specified, we expect `coords`
        to be a list (resp. tuple) of the form ``[top_left, bottom_right]``
        (resp. ``(top_left, bottom_right)``)

    start_date: datetime.datetime
        First date of the time interval

    end_date: datetime.datetime
        Last date of the time interval

    ascending : boolean, optional
        The trajectory to use when selecting data

    scale : int, optional
        Scale parameters of the getRegion() function. Defaulting at ``20``,
        change it to change the scale of the final data points. The highest,
        the lower the spatial resolution. Should be at least ``10``.

    n_jobs: int
        Defines the number of threads used for the parallelisation of date acquisitions

    ascending: bool

    Returns
    -------
    `list`
        A list of dictionnaries, each providing data over one given coordinate.
    '''

    orbit = ASCENDING if ascending else DESCENDING

    if (top_left is not None):
        list_of_coordinates = [make_polygon(top_left, bottom_right)]
    else:
        list_of_coordinates = [coords]

    date_intervals = get_date_interval_array(start_date, end_date)

    # retrieving the number of pixels per image
    try:
        polygon = ee.Geometry.Polygon(list_of_coordinates)
        _ = fetch_sentinel1_data(
            start_date=date_intervals[0][0],
            end_date=date_intervals[-1][1],
            geometry=polygon,
            scale=scale,
            orbit=orbit,
        )
    except Exception as e:
        # If the area is found to be too big
        if (str(e) == "ImageCollection.getRegion: No bands in collection."):
            raise IncorrectOrbitException(orbit)
        total_count_of_pixels = retrieve_max_pixel_count_from_pattern(str(e))
        if top_left is not None:
            list_of_coordinates = tile_coordinates(
                total_count_of_pixels, (top_left, bottom_right))
        else:
            list_of_coordinates = tile_coordinates(
                total_count_of_pixels, coords)


    print(f"Region sliced in {len(list_of_coordinates)} subregions and {len(date_intervals)} time intervals.")

    per_coord_dict = {}
    for c in tqdm(list_of_coordinates):
        vals = []
        headers = []
        polygon = ee.Geometry.Polygon([
            c
        ])
        # Updates vals and headers, one by aggregating returned values of the delayed function, the other by modifying the passed `headers` argument
        vals = Parallel(n_jobs=n_jobs, require="sharedmem")(delayed(_get_zone_between_dates)(sub_start_date, sub_end_date, polygon, scale, orbit, headers) for sub_start_date, sub_end_date in date_intervals)
        vals = [val for val in vals if val is not None]
        dictified_vals = [dict(zip(headers, val)) for values in vals for val in values]
        per_coord_dict = populate_coordinates_dictionary(
                dictified_values=dictified_vals,
                coordinates_dictionary=per_coord_dict,
        )
    pixel_values = [per_coord_dict[k] for k in per_coord_dict.keys()]
    cmp_coordinates = cmp_to_key(cmp_coords)
    pixel_values.sort(key=cmp_coordinates)  # sorting pixels by latitude then longitude
    
    return pixel_values

def get_point_pixel_values(coords, start_date: datetime = date.today()-timedelta(days=365), end_date: datetime = date.today(), ascending: bool = True, scale=20, n_jobs=1):
    '''Given a coordinate tuple and a list of date intervals, loops over both to agglomerate GEE sar pixel values and returns a list of dictionnaries, with intesities and timestamps.
    The main loop, over dates, is parallelised.


    Parameters
    ----------
    coords : tuple of float
        Coordinates (lon, lat) of the point of interest 
    
    start_date : datetime.datetime, optional
        First date of the time interval

    end_date : datetime.datetime, optional
        Last date of the time interval

    ascending : boolean, optional
        The trajectory to use when selecting data

    scale : int, optional
        Scale parameters of the getRegion() function. Defaulting at ``20``,
        change it to change the scale of the final data points. The highest,
        the lower the spatial resolution. Should be at least ``10``.

    n_jobs : int, optional
        Set the parallelisation factor (number of threads) for the GEE data
        access process. Set to 1 if no parallelisation required.

    Returns
    -------
    `list`
        A list with a single dictionnary, to match the behaviour of :func:`get_pixel_values` for a single point.
    '''
    orbit = ASCENDING if ascending else DESCENDING
    date_intervals = get_date_interval_array(start_date, end_date)
    polygon = ee.Geometry.Point(coords)
    headers = []
    # Updates vals and headers, one by aggregating returned values of the delayed function, the other by modifying the passed `headers` argument
    vals = Parallel(n_jobs=n_jobs, require="sharedmem")(delayed(_get_zone_between_dates)(sub_start_date, sub_end_date, polygon, scale, orbit, headers) for sub_start_date, sub_end_date in tqdm(date_intervals))
    vals = [val for val in vals if val is not None]
    dictified_vals = [dict(zip(headers, val)) for values in vals for val in values]
    per_coord_dict = populate_coordinates_dictionary(
        dictified_values=dictified_vals,
        coordinates_dictionary={}
    )

    pixel_values = [per_coord_dict[k] for k in per_coord_dict.keys()]
    cmp_coordinates = cmp_to_key(cmp_coords)
    pixel_values.sort(key=cmp_coordinates)  # sorting pixels by latitude then longitude
    
    return pixel_values

def get_timestamps_from_pixel_values(pixel_values):
    '''Given a pixel_values object from :func:`get_pixel_values`, retrieves a list of each unique acquisition days

    Parameters
    ----------
    pixel_values: list


    '''

    timestamps = np.unique(
            [
                datetime.fromtimestamp(pixel_values[i]['timestamps'][j]).date()
                for i in range(len(pixel_values))
                for j in range(len(pixel_values[i]['timestamps']))
            ]
    )

    return timestamps

def generate_image(timestamps, pixel_values):
    '''Given a list of timestamps and an array of pixel_values as :func:`~get_pixel_values`, generate a numpy matrix. Missing coordinates/dates will be inplaced with NaNs.

    Parameters
    ----------
    timestamps: list, or numpy.ndarray
        A list of unique dates (unicity is respected by measures of day: i.e, two acquisitions on the same day will be averaged)
    
    pixel_values: list
        A list of dictionnaries, each providing data over one given coordinate, preferably returned by :func:`~get_pixel_values`

    Returns
    -------
    `tuple`
        Returns a tuple containing the 4-D image as a `numpy.ndarray` of shape ``(height, width, polarisations, time)`` and a coordinates matrix, affecting to each pixel of the image its respective coordinate, of shape ``(height, width, 2)``.

    '''

    # Creating matrix of coordinates
    lats, lons = tuple(zip(*[(p["lat"], p["lon"]) for p in pixel_values]))
    
    unique_lats = np.unique(lats)
    unique_lats = unique_lats[::-1]
    lats_dict = {unique_lats[i]: i for i in range(len(unique_lats))}

    unique_lons = np.unique(lons)
    lons_dict = {unique_lons[i]: i for i in range(len(unique_lons))}

    width, height = len(unique_lons), len(unique_lats)
    coordinates = [[lat, lon] for lat in unique_lats for lon in unique_lons]
    coordinates = np.array(coordinates).reshape(height, width, 2)

    img = np.full((height, width, 2, len(timestamps)),fill_value=np.nan)

    print(f"Generating image of shape {height, width}")
    for p in tqdm(pixel_values):
        x, y = lats_dict[p["lat"]], lons_dict[p["lon"]]
        vv = []
        vh = []
        for timestamp in timestamps:

            indexes = np.argwhere(
                np.array([datetime.fromtimestamp(p_t).date() for p_t in p["timestamps"]]) == timestamp
            )
            vv.append(np.nanmean(
                np.array(p["VV"], dtype=float)[indexes]))
            vh.append(np.nanmean(
                np.array(p["VH"], dtype=float)[indexes]))

        img[x, y, 0, :] = vv
        img[x, y, 1, :] = vh
    return img, coordinates