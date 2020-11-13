"""geesarfetcher"""

__version__ = "0.2.0"

# LIBRARY IMPORTS
import ee
import warnings
from datetime import datetime, date, timedelta
from tqdm import tqdm
from functools import cmp_to_key
import numpy as np
from joblib import Parallel, delayed

# LOCAL IMPORTS
from .utils import make_polygon
from .utils import tile_coordinates
from .utils import define_image_shape
from .utils import retrieve_max_pixel_count_from_pattern
from .utils import cmp_coords
from .utils import get_date_interval_array
from .constants import ASCENDING, DESCENDING
from .filter import filter_sentinel1_data
from .fetcher import fetch_sentinel1_data
from .coordinates import populate_coordinates_dictionary

warnings.simplefilter(action="ignore")
ee.Initialize()

def fetch(
    top_left=None,
    bottom_right=None,
    coords=None,
    start_date: datetime = date.today()-timedelta(days=365),
    end_date: datetime = date.today(),
    ascending: bool = True,
    scale: int = 20,
    n_jobs: int = 8
):
    '''Fetches SAR data in the form of a dictionnary with image data as well as timestamps

    Parameters
    ----------
    top_left : tuple of float, optional
        Top left coordinates (lon, lat) of the Region 
    bottom_right : tuple of float, optional
        Bottom right coordinates (lon, lat) of the Region
    coords : tuple of tuple of float or list of list of float, optional
        If `top_left` and `bottom_right` are not specified, we expect `coords` to be a list (resp. tuple) of the form ``[top_left, bottom_right]`` (resp. ``(top_left, bottom_right)``)
    start_date : datetime.datetime, optional
        First date of the time interval
    end_date : datetime.datetime, optional
        Last date of the time interval
    ascending : boolean, optional
        The trajectory to use when selecting data
    scale : int, optional
        Scale parameters of the getRegion() function. Defaulting at ``20``, change it to change the scale of the final data points. The highest, the lower the spatial resolution. Should be at least ``10``.
    n_jobs : int, optional
        Set the parallelisation factor (number of threads) for the GEE data access process. Set to 1 if no parallelisation required. 
    Returns
    -------
    `dict`
        Dictionnary with two keys:

            ``"stacks"``
                4-D array containing db intensity measure (`numpy.ndarray`), ``(height, width, time_series_length, pol_count)``
            ``"coordinates"``
                3-D array containg coordinates where ``[:,:,0]`` provides access to latitude and ``[:,:,1]`` provides access to longitude, (`numpy.ndarray`), ``(height, width, 2)``
            ``"timestamps"``
                list of acquisition timestamps of size (time_series_length,) (`list of str`)
            ``"metadata"``
                Dictionnary describing data for each axis of the stack and the coordinates

    '''

    assert(coords is None or (
        (type(coords) == list or type(coords) == tuple) and len(coords) == 2) and len(coords[0]) == len(coords[1]) and len(coords[0]) == 2)

    assert((top_left is None and bottom_right is None)
           or (type(top_left) == type(bottom_right) and (type(top_left) == tuple or type(top_left) == list))
           and len(top_left) == len(bottom_right) and len(top_left) == 2)

    assert(start_date is not None)
    assert(end_date is not None)
    assert(end_date > start_date)

    if top_left is not None and bottom_right is not None and coords is not None:
        raise ValueError(
            "coords must be None if top_left and bottom_right are not None.")

    date_intervals = get_date_interval_array(start_date, end_date)
    orbit = ASCENDING if ascending else DESCENDING

    if (top_left is not None):
        list_of_coordinates = [make_polygon(top_left, bottom_right)]
    else:
        list_of_coordinates = [coords]

    # retrieving the number of pixels per image
    try:
        polygon = ee.Geometry.Polygon(list_of_coordinates)
        sentinel_1_roi = filter_sentinel1_data(
            start_date=date_intervals[0][0],
            end_date=date_intervals[-1][1],
            geometry=polygon,
            orbit=orbit,
        )
        _ = (sentinel_1_roi
                  .select("VV")
                  .getRegion(polygon, scale=scale)
                  .getInfo()
        )

    except Exception as e:

        # If the area is found to be too big
        if (str(e) == "ImageCollection.getRegion: No bands in collection."):
            raise ValueError(
                "No bands found in collection. Orbit incorrect for localisation, please visit https://sentinel.esa.int/web/sentinel/missions/sentinel-1/observation-scenario for more info.")
        total_count_of_pixels = retrieve_max_pixel_count_from_pattern(str(e))
        if top_left is not None:
            list_of_coordinates = tile_coordinates(
                total_count_of_pixels, (top_left, bottom_right))
        else:
            list_of_coordinates = tile_coordinates(
                total_count_of_pixels, coords)

    per_coord_dict = {}

    ###################################
    ## RETRIEVING COORDINATES VALUES ##
    ## FOR EACH DATE INTERVAL        ##
    ###################################
    print(f"Region sliced in {len(list_of_coordinates)} subregions and {len(date_intervals)} time intervals.")


    def _get_zone_between_dates(start_date, end_date, polygon, scale, orbit):
        try:
            val_header, val = fetch_sentinel1_data(
                start_date=start_date,
                end_date=end_date,
                geometry=polygon,
                orbit=orbit,
                scale=scale
            )
            vals.extend(val)

            if len(headers) == 0:
                headers.extend(val_header)
            vals.extend(val)
        except Exception as e:
            pass

    for c in tqdm(list_of_coordinates):
        vals = []
        headers = []
        polygon = ee.Geometry.Polygon([
            c
        ])
        # Fill vals with values.
        # TODO: Evaluate eventuality to remove shared memory requirement and to exploit automatic list building from Joblib
        Parallel(n_jobs=n_jobs, require='sharedmem')(delayed(_get_zone_between_dates)(sub_start_date, sub_end_date, polygon, scale, orbit) for sub_start_date, sub_end_date in date_intervals)

        dictified_vals = [dict(zip(headers, values)) for values in vals]
        per_coord_dict = populate_coordinates_dictionary(
                dictified_values=dictified_vals,
                coordinates_dictionary=per_coord_dict,
        )

    # per_coord_dict is a dictionnary matching to each coordinate key its values through time as well as its timestamps

    ##############################
    ## BUILDING TEMPORAL IMAGES ##
    ##############################

    pixel_values = [per_coord_dict[k] for k in per_coord_dict.keys()]
    cmp_coordinates = cmp_to_key(cmp_coords)
    pixel_values.sort(key=cmp_coordinates)  # sorting pixels by latitude then longitude
    timestamps = np.unique(
            [
                datetime.fromtimestamp(pixel_values[i]['timestamps'][j]).date()
                for i in range(len(pixel_values))
                for j in range(len(pixel_values[i]['timestamps']))
            ]
    )
    width, height = define_image_shape(pixel_values)
    print(f"Generating image of shape {height, width}")
    def _update_img(pixel_value):
        vv = []
        vh = []
        for timestamp in timestamps:

            indexes = np.argwhere(
                np.array([datetime.fromtimestamp(p_t).date() for p_t in pixel_value["timestamps"]]) == timestamp
            )
            vv.append(np.nanmean(
                np.array(pixel_value["VV"], dtype=float)[indexes]))
            vh.append(np.nanmean(
                np.array(pixel_value["VH"], dtype=float)[indexes]))
        return [vv, vh]

    indexes = [(i,j) for i in range(height) for j in range(width)]


    vals = Parallel(n_jobs=n_jobs)(
        delayed(_update_img)(pixel_values[i*width + j]) for (i,j) in tqdm(indexes)
    )
    img = np.array(vals).reshape((height, width, 2, len(timestamps)))

    lats, lons = tuple(zip(*[(p["lat"], p["lon"]) for p in pixel_values]))

    lats = np.array(lats).reshape((height, width))
    lons = np.array(lons).reshape((height, width))

    coordinates = np.zeros((height, width,2))
    coordinates[:,:,0] = lats
    coordinates[:,:,1] = lons

    return {
        "stack": img,
        "timestamps": timestamps,
        "coordinates": coordinates,
        "metadata": {
            "stack": {
                "axis_0": "height",
                "axis_1": "width",
                "axis_2": "polarisations (0:VV, 1:VH)",
                "axis_3": "timestamps"
            },
            "coordinates": {
                "axis_0": "height",
                "axis_1": "width",
                "axis_2": "0:latitude; 1:longitude",
            }
        }
    }

