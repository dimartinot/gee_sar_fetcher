"""geesarfetcher"""

__version__ = "0.1.0"

# LIBRARY IMPORTS
import ee
import warnings
from datetime import datetime, date, timedelta
from tqdm import tqdm
from functools import cmp_to_key
import numpy as np

# LOCAL IMPORTS
from geesarfetcher.utils import *

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
        polygon = ee.Geometry.Polygon([
            [top_left],  # top-left
            [top_left[0], bottom_right[1]],  # top-right
            [bottom_right],  # bottom-right
            [bottom_right[0], top_left[1]],
            [top_left]
        ])
    else:
        polygon = ee.Geometry.Polygon([
            coords
        ])

    # retrieving the number of pixels per image
    try:
        # Call collection of satellite images.
        sentinel_1_roi = (ee.ImageCollection("COPERNICUS/S1_GRD")
                          # Filter for images within a given date range.
                          .filter(ee.Filter.date(date_intervals[0][0], date_intervals[-1][1]))
                          # Filter for images that overlap with the assigned geometry.
                          .filterBounds(polygon)
                          # Filter orbit
                          .filter(ee.Filter.inList('transmitterReceiverPolarisation', 'VV'))
                          .filter(ee.Filter.inList('transmitterReceiverPolarisation', 'VH'))
                          # Filter to get images collected in interferometric wide swath mode.
                          .filter(ee.Filter.eq('instrumentMode', 'IW'))
                          .filter(ee.Filter.eq('orbitProperties_pass', orbit))
                          .filter(ee.Filter.eq('resolution_meters', 10))
                          )
        val_vv = sentinel_1_roi.select("VV").getRegion(polygon).getInfo()

    # take into account different exceptiuons ("no band found in collection")
    except Exception as e:
        if (str(e) == "ImageCollection.getRegion: No bands in collection."):
            raise ValueError(
                "No bands found in collection. Orbit incorrect for localisation, please visit https://sentinel.esa.int/web/sentinel/missions/sentinel-1/observation-scenario for more info.")
        total_count_of_pixels = retrieve_max_pixel_count_from_pattern_(str(e))

    if top_left is not None:
        list_of_coordinates = tile_coordinates(
            total_count_of_pixels, (top_left, bottom_right))
    else:
        list_of_coordinates = tile_coordinates(total_count_of_pixels, coords)

    vals = []
    per_coord_dict = {}

    ###################################
    ## RETRIEVING COORDINATES VALUES ##
    ## FOR EACH DATE INTERVAL        ##
    ###################################

    for sub_start_date, sub_end_date in tqdm(date_intervals):
        for c in list_of_coordinates:
            polygon = ee.Geometry.Polygon([
                c
            ])
            try:
                # Call collection of satellite images.
                sentinel_1_roi = (ee.ImageCollection("COPERNICUS/S1_GRD")
                                  # Filter for images within a given date range.
                                  .filter(ee.Filter.date(sub_start_date, sub_end_date))
                                  # Filter for images that overlap with the assigned geometry.
                                  .filterBounds(polygon)
                                  # Filter orbit
                                  .filter(ee.Filter.inList('transmitterReceiverPolarisation', 'VV'))
                                  .filter(ee.Filter.inList('transmitterReceiverPolarisation', 'VH'))
                                  # Filter to get images collected in interferometric wide swath mode.
                                  .filter(ee.Filter.eq('instrumentMode', 'IW'))
                                  .filter(ee.Filter.eq('orbitProperties_pass', orbit))
                                  .filter(ee.Filter.eq('resolution_meters', 10))
                                  )
                val_vv = sentinel_1_roi.select(
                    "VV").getRegion(polygon).getInfo()
                val_vh = sentinel_1_roi.select(
                    "VH").getRegion(polygon).getInfo()

                val_vv = [
                    [val_vv[i][0] + ["VV"], val_vv[i][1] + [val_vh[i][1][val_vh[i][0].index("VH")]]] for i in range(len(val_vv))
                ]

                vals.extend(val_vv)

            # take into account different exceptiuons ("no band found in collection")
            except Exception as e:
                if (str(e) == "ImageCollection.getRegion: No bands in collection."):
                    raise ValueError(
                        "No bands found in collection. Orbit incorrect for localisation, please visit https://sentinel.esa.int/web/sentinel/missions/sentinel-1/observation-scenario for more info.")
                total_count_of_pixels = retrieve_max_pixel_count_from_pattern_(
                    str(e))

        dictified_vals = [dict(zip(vals[0], values)) for values in vals[1:]]
        for entry in dictified_vals:
            lat = entry["latitude"]
            lon = entry["longitude"]

            new_key = str(lat)+":"+str(lon)

            if new_key in per_coord_dict:
                # Retrieving measured value
                per_coord_dict[new_key]["VV"].append(entry["VV"])
                per_coord_dict[new_key]["VH"].append(entry["VH"])

                datetime = entry["id"].split("_")[4]

                per_coord_dict[new_key]["timestamps"].append(datetime)

            else:
                per_coord_dict[new_key] = {}
                # Retrieving measured value
                per_coord_dict[new_key]["lat"] = lat
                per_coord_dict[new_key]["lon"] = lon
                per_coord_dict[new_key]["VV"] = [entry["VV"]]
                per_coord_dict[new_key]["VH"] = [entry["VH"]]

                datetime = entry["id"].split("_")[4]

                per_coord_dict[new_key]["timestamps"] = [datetime]

    # per_coord_dict is a dictionnary matching to each coordinate key its values through time as well as its timestamps

    ##############################
    ## BUILDING TEMPORAL IMAGES ##
    ##############################

    pixel_values = [per_coord_dict[k] for k in per_coord_dict.keys()]
    cmp_coordinates = cmp_to_key(cmp_coords)

    # sorting pixels by latitude then longitude
    pixel_values.sort(key=cmp_coordinates)

    # we assume similar dates for each pixels
    date_count = len(pixel_values[0]['VV'])

    # counting pixels with common latitude until it changes to know the image width
    width = 1
    while pixel_values[width]["lat"] == pixel_values[0]["lat"]:
        width += 1

    # deducing the image height from its width
    height = len(pixel_values) // width

    img = np.zeros((height, width) + (date_count, 2))  # VV & VH bands

    for i in range(height):
        for j in range(width):
            img[i][j][0] = pixel_values[i*width + j]["VV"]
            img[i][j][1] = pixel_values[i*width + j]["VH"]

    return {
        "stack": img,
        "timestamps": pixel_values[0]['timestamps']
    }