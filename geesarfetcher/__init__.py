"""geesarfetcher"""

__version__ = "0.1.1"

# LIBRARY IMPORTS
import ee
import warnings
from datetime import datetime, date, timedelta
from tqdm import tqdm
from functools import cmp_to_key
import numpy as np

# LOCAL IMPORTS
from geesarfetcher.utils import *
from geesarfetcher.filter import filter_sentinel1_data
from geesarfetcher.fetcher import fetch_sentinel1_data

warnings.simplefilter(action="ignore")
ee.Initialize()

def fetch(
    top_left=None,
    bottom_right=None,
    coords=None,
    start_date: datetime = date.today()-timedelta(days=365),
    end_date: datetime = date.today(),
    ascending: bool = True
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

    Returns
    -------
    `dict`
        Dictionnary with two keys:

            ``"stacks"``
                4-D array containing db intensity measure (`numpy.ndarray`), ``(height, width, time_series_length, pol_count)``
            ``"timestamps"``
                list of acquisition timestamps of size (time_series_length,) (`list of str`)
            ``"metadata"``
                Dictionnary describing data for each axis of the stack

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
    orbit = "ASCENDING" if ascending else "DESCENDING"

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
        val_vv = sentinel_1_roi.select("VV").getRegion(
            polygon, scale=10).getInfo()

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
    print(
        f"Region sliced in {len(list_of_coordinates)} subregions and {len(date_intervals)} time intervals.")

    vals = []
    val_header = []
    for sub_start_date, sub_end_date in tqdm(date_intervals):
        for c in list_of_coordinates:

            polygon = ee.Geometry.Polygon([
                c
            ])
            try:
                val_header, val = fetch_sentinel1_data(
                        start_date=sub_start_date,
                        end_date=sub_end_date,
                        geometry=polygon,
                        orbit=orbit,
                )
                vals.extend(val)
            except Exception as e:
                pass  # passing date, no data found for this time interval

    dictified_vals = [dict(zip(val_header, values)) for values in vals]

    for entry in dictified_vals:
        lat = entry["latitude"]
        lon = entry["longitude"]

        new_key = str(lat)+":"+str(lon)

        if new_key in per_coord_dict:
            # Retrieving measured value
            per_coord_dict[new_key]["VV"].append(entry["VV"])
            per_coord_dict[new_key]["VH"].append(entry["VH"])

            datetime = entry["id"].split("_")[4]

            per_coord_dict[new_key]["timestamps"].append(datetime[:8])

        else:
            per_coord_dict[new_key] = {}
            # Retrieving measured value
            per_coord_dict[new_key]["lat"] = lat
            per_coord_dict[new_key]["lon"] = lon
            per_coord_dict[new_key]["VV"] = [entry["VV"]]
            per_coord_dict[new_key]["VH"] = [entry["VH"]]

            datetime = entry["id"].split("_")[4]

            per_coord_dict[new_key]["timestamps"] = [datetime[:8]]

    # per_coord_dict is a dictionnary matching to each coordinate key its values through time as well as its timestamps

    ##############################
    ## BUILDING TEMPORAL IMAGES ##
    ##############################

    pixel_values = [per_coord_dict[k] for k in per_coord_dict.keys()]
    cmp_coordinates = cmp_to_key(cmp_coords)

    # sorting pixels by latitude then longitude
    pixel_values.sort(key=cmp_coordinates)

    timestamps = np.unique([pixel_values[i]['timestamps'][j] for i in range(
        len(pixel_values)) for j in range(len(pixel_values[i]['timestamps']))])
    date_count = len(timestamps)

    # counting pixels with common latitude until it changes to know the image width
    width = 1
    while pixel_values[width]["lat"] == pixel_values[0]["lat"]:
        width += 1

    # deducing the image height from its width
    height = len(pixel_values) // width

    img = np.zeros((height, width) + (2, date_count))  # VV & VH bands

    for i in range(height):
        for j in range(width):
            for t, timestamp in enumerate(timestamps):
                indexes = np.argwhere(
                    np.array(pixel_values[i*width + j]
                             ["timestamps"]) == timestamp
                )
                img[i, j, 0, t] = np.nanmean(
                    np.array(pixel_values[i*width + j]["VV"], dtype=float)[indexes])
                img[i, j, 1, t] = np.nanmean(
                    np.array(pixel_values[i*width + j]["VH"], dtype=float)[indexes])

    return {
        "stack": img,
        "timestamps": timestamps,
        "metadata": {
            "axis_0": "height",
            "axis_1": "width",
            "axis_2": "polarisations (0:VV, 1:VH)",
            "axis_3": "timestamps"
        }
    }

    