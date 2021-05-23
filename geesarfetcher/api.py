# LIBRARY IMPORTS
import ee
from datetime import datetime, date, timedelta
from numpy.lib.function_base import iterable
from tqdm import tqdm
from functools import cmp_to_key
import numpy as np
from joblib import Parallel, delayed
import os
import ntpath
import json

# LOCAL IMPORTS
from .constants import ASCENDING, DESCENDING
from .coordinates import populate_coordinates_dictionary
from .exceptions import IncorrectOrbitException
from .filter import filter_sentinel1_data
from .fetcher import fetch_sentinel1_data
from .fetcher import _get_zone_between_dates
from .fetcher import _get_properties_between_dates
from .utils import make_polygon
from .utils import tile_coordinates
from .utils import retrieve_max_pixel_count_from_pattern
from .utils import cmp_coords
from .utils import get_date_interval_array
from .utils import print_verbose


def get_pixel_values(
    top_left=None,
    bottom_right=None,
    coords=None,
    start_date: datetime = date.today() - timedelta(days=365),
    end_date: datetime = date.today(),
    ascending: bool = True,
    orbit_number: object = None,
    scale=20,
    n_jobs=1,
    verbose=0,
):
    """Given a list of coordinates and another of date intervals, loops over both to agglomerate GEE sar pixel values and returns a list of dictionnaries, one per coordinate, with intensities and timestamps.
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

    orbit_number : int or str, optional
        The orbit number to restrict the download to. If provided with an integer, the S1 temporal stack is filtered using the provided orbit number.
        If provided with a string value, we expect one of these keywords:
         - "max" for the orbit number with the highest number of image in the stack
         - "min" for the orbit number with the smallest number of image in the stack
        If ``None``, then no filter over the orbit number is applied.

    scale : int, optional
        Scale parameters of the getRegion() function. Defaulting at ``20``,
        change it to change the scale of the final data points. The highest,
        the lower the spatial resolution. Should be at least ``10``.

    n_jobs : int, optional
        Defines the number of threads used for the parallelisation of date acquisitions

    verbose : int, optional
        Verbosity mode (0: No info, 1: Info, 2: Detailed info, with added timestamp)

    Returns
    -------
    `list`
        A list of dictionnaries, each providing data over one given coordinate.
    """

    orbit = ASCENDING if ascending else DESCENDING

    list_of_coordinates = split_coordinates(
        top_left, bottom_right, coords, start_date, end_date, ascending, scale
    )

    if orbit_number is not None and type(orbit_number) == str:
        orbit_number = get_orbit_number(
            top_left,
            bottom_right,
            coords,
            start_date,
            end_date,
            ascending,
            orbit_number,
            scale,
        )

    if orbit_number is not None:
        print_verbose(f"Selected orbit: {orbit_number}", verbose, 1)

    date_intervals = get_date_interval_array(start_date, end_date)

    print_verbose(
        f"Region sliced in {len(list_of_coordinates)} subregions and {len(date_intervals)} time intervals.",
        verbose,
        1,
    )
    print_verbose(f"Generating values for each subcoordinate", verbose, 1)
    per_coord_dict = {}

    properties = []
    for n, c in enumerate(list_of_coordinates):
        print_verbose(f"Starting process for subcoordinate n°{n}", verbose, 1)
        vals = []
        headers = []
        polygon = ee.Geometry.Polygon([c])
        # Updates vals and headers, one by aggregating returned values of the delayed function, the other by modifying the passed `headers` argument
        vals = Parallel(n_jobs=n_jobs, require="sharedmem")(
            delayed(_get_zone_between_dates)(
                sub_start_date,
                sub_end_date,
                polygon,
                scale,
                orbit,
                orbit_number,
                headers,
            )
            for sub_start_date, sub_end_date in tqdm(date_intervals)
        )
        vals = [val for val in vals if val is not None]
        dictified_vals = [dict(zip(headers, val)) for values in vals for val in values]
        per_coord_dict = populate_coordinates_dictionary(
            dictified_values=dictified_vals,
            coordinates_dictionary=per_coord_dict,
        )

        tmp_properties = Parallel(n_jobs=n_jobs, require="sharedmem")(
            delayed(_get_properties_between_dates)(
                sub_start_date, sub_end_date, polygon, orbit, orbit_number
            )
            for sub_start_date, sub_end_date in tqdm(date_intervals)
        )
        tmp_properties = [p for p in tmp_properties if p is not None]
        properties.append(tmp_properties)
        print_verbose(f"Ending process for subcoordinate n°{n}", verbose, 2)

    print_verbose(f"Sorting pixel values by coordinates", verbose, 2)
    pixel_values = [per_coord_dict[k] for k in per_coord_dict.keys()]
    cmp_coordinates = cmp_to_key(cmp_coords)
    pixel_values.sort(key=cmp_coordinates)  # sorting pixels by latitude then longitude
    print_verbose(f"Pixel values sorted...", verbose, 2)

    print_verbose(f"Transforming properties...", verbose, 1)

    return pixel_values, properties


def get_point_pixel_values(
    coords,
    start_date: datetime = date.today() - timedelta(days=365),
    end_date: datetime = date.today(),
    ascending: bool = True,
    orbit_number: object = None,
    scale: int = 20,
    n_jobs: int = 1,
    verbose: int = 0,
):
    """Given a coordinate tuple and a list of date intervals, loops over both to agglomerate GEE sar pixel values and returns a list of dictionnaries, with intensities and timestamps.
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

    orbit_number : int or str, optional
        The orbit number to restrict the download to. If provided with an integer, the S1 temporal stack is filtered using the provided orbit number.
        If provided with a string value, we expect one of these keywords:
         - "max" for the orbit number with the highest number of image in the stack
         - "min" for the orbit number with the smallest number of image in the stack
        If ``None``, then no filter over the orbit number is applied.

    scale : int, optional
        Scale parameters of the getRegion() function. Defaulting at ``20``,
        change it to change the scale of the final data points. The highest,
        the lower the spatial resolution. Should be at least ``10``.

    n_jobs : int, optional
        Set the parallelisation factor (number of threads) for the GEE data
        access process. Set to 1 if no parallelisation required.

    verbose : int, optional
        Verbosity mode (0: No info, 1: Info, 2: Detailed info, with added timestamp)

    Returns
    -------
    `list`
        A list with a single dictionnary, to match the behaviour of :func:`get_pixel_values` for a single point.
    """
    orbit = ASCENDING if ascending else DESCENDING
    date_intervals = get_date_interval_array(start_date, end_date)
    polygon = ee.Geometry.Point(coords)
    headers = []

    if orbit_number is not None and type(orbit_number) == str:
        orbit_number = get_orbit_number(
            coords=coords,
            start_date=start_date,
            end_date=end_date,
            ascending=ascending,
            orbit_number=orbit_number,
            scale=scale,
        )

    if orbit_number is not None:
        print_verbose(f"Selected orbit: {orbit_number}", verbose, 1)

    print_verbose(f"Generating values for each time interval", verbose, 1)
    # Updates vals and headers, one by aggregating returned values of the delayed function, the other by modifying the passed `headers` argument
    vals = Parallel(n_jobs=n_jobs, require="sharedmem")(
        delayed(_get_zone_between_dates)(
            sub_start_date, sub_end_date, polygon, scale, orbit, orbit_number, headers
        )
        for sub_start_date, sub_end_date in tqdm(date_intervals)
    )

    print_verbose(f"Retrieving data properties for each time interval", verbose, 1)
    properties = Parallel(n_jobs=n_jobs, require="sharedmem")(
        delayed(_get_properties_between_dates)(
            sub_start_date, sub_end_date, polygon, orbit, orbit_number
        )
        for sub_start_date, sub_end_date in tqdm(date_intervals)
    )

    properties = [p for p in properties if p is not None]

    properties = np.array([properties])

    vals = [val for val in vals if val is not None]
    dictified_vals = [dict(zip(headers, val)) for values in vals for val in values]
    per_coord_dict = populate_coordinates_dictionary(
        dictified_values=dictified_vals, coordinates_dictionary={}
    )

    pixel_values = [per_coord_dict[k] for k in per_coord_dict.keys()]
    cmp_coordinates = cmp_to_key(cmp_coords)
    pixel_values.sort(key=cmp_coordinates)  # sorting pixels by latitude then longitude

    return pixel_values, properties


def get_timestamps_from_pixel_values(pixel_values):
    """Given a pixel_values object from :func:`get_pixel_values`, retrieves a list of each unique acquisition days

    Parameters
    ----------
    pixel_values: list


    """

    timestamps = np.unique(
        [
            datetime.fromtimestamp(pixel_values[i]["timestamps"][j]).date()
            for i in range(len(pixel_values))
            for j in range(len(pixel_values[i]["timestamps"]))
        ]
    )

    return timestamps


def generate_image(timestamps, pixel_values, properties, verbose=0):
    """Given a list of timestamps and an array of pixel_values as :func:`~get_pixel_values`, generates a numpy matrix. Missing coordinates/dates will be inplaced with NaNs.

    Parameters
    ----------
    timestamps: list, or numpy.ndarray
        A list of unique dates (unicity is respected by measures of day: i.e, two acquisitions on the same day will be averaged)

    pixel_values: list
        A list of dictionnaries, each providing data over one given coordinate, preferably returned by :func:`~get_pixel_values`

    properties: list
        A list of list of properties

    verbose : int, optional
        Verbosity mode (0: No info, 1: Info, 2: Detailed info, with added timestamp)

    Returns
    -------
    `tuple`
        Returns a tuple containing the 4-D image as a `numpy.ndarray` of shape ``(height, width, polarisations, time)`` and a coordinates matrix, affecting to each pixel of the image its respective coordinate, of shape ``(height, width, 2)``.

    """

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

    img = np.full((height, width, 2, len(timestamps)), fill_value=np.nan)

    # we transform the properties object from a list of list to a list of dictionnary l = [t1, t2, t3..] where ti = {subimage1:[{...}], subimage2:[{...}], ..., subimagen:[{...}]}
    # if two images overlaps in a given subcoordinate polygon, we merge them by mean and keep these two seperate properties information
    n_properties = [
        {i: [] for i in range(len(properties))} for _ in range(len(timestamps))
    ]

    for n, subcoordinate_properties in enumerate(properties):
        for ts in subcoordinate_properties:

            for i in range(len(timestamps)):
                if (
                    timestamps[i]
                    == datetime.fromtimestamp(ts["system:time_start"] // 1000).date()
                ):
                    n_properties[i][n].append(ts)
    for n in range(len(properties)):
        for i in range(len(timestamps)):
            if len(n_properties[i][n]) > 1:
                new_field = {
                    f"subimage_{j}": n_properties[i][n][j]
                    for j in range(len(n_properties[i][n]))
                }
                n_properties[i][n] = new_field

    print_verbose(f"Generating image of shape {height, width}", verbose, 1)

    if verbose >= 1:
        iterator = tqdm(pixel_values)
    else:
        iterator = pixel_values

    for p in iterator:
        x, y = lats_dict[p["lat"]], lons_dict[p["lon"]]
        vv = []
        vh = []
        for timestamp in timestamps:

            indexes = np.argwhere(
                np.array(
                    [datetime.fromtimestamp(p_t).date() for p_t in p["timestamps"]]
                )
                == timestamp
            )

            vv.append(np.nanmean(np.array(p["VV"], dtype=float)[indexes]))
            vh.append(np.nanmean(np.array(p["VH"], dtype=float)[indexes]))

        img[x, y, 0, :] = vv
        img[x, y, 1, :] = vh
    return img, coordinates, n_properties


def split_coordinates(
    top_left=None,
    bottom_right=None,
    coords=None,
    start_date: datetime = date.today() - timedelta(days=365),
    end_date: datetime = date.today(),
    ascending: bool = True,
    scale: int = 20,
):
    """Given coordinates of the whole area, splits it into a list of subcoordinates if needed by GEE.

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

    Returns
    -------
    `list`
        List of subcoordinates

    """
    orbit = ASCENDING if ascending else DESCENDING

    if top_left is not None:
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
        if str(e) == "ImageCollection.getRegion: No bands in collection.":
            raise IncorrectOrbitException(orbit)
        total_count_of_pixels = retrieve_max_pixel_count_from_pattern(str(e))
        if top_left is not None:
            list_of_coordinates = tile_coordinates(
                total_count_of_pixels, (top_left, bottom_right)
            )
        else:
            list_of_coordinates = tile_coordinates(total_count_of_pixels, coords)

    return list_of_coordinates


def get_orbit_number(
    top_left=None,
    bottom_right=None,
    coords=None,
    start_date: datetime = date.today() - timedelta(days=365),
    end_date: datetime = date.today(),
    ascending: bool = True,
    orbit_number: str = "max",
    scale: int = 20,
):
    """Given coordinates of the whole area, and orbit number selection mode, retrieves the adequate orbit number for the given temporal stack.

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

    start_date : datetime.datetime, optional
        First date of the time interval

    end_date : datetime.datetime, optional
        Last date of the time interval

    ascending : boolean, optional
        The trajectory to use when selecting data


    orbit_number : str, optional
        The orbit number option. We expect one of these keywords:
         - "max" for the orbit number with the highest number of image in the stack
         - "min" for the orbit number with the smallest number of image in the stack

    scale : int, optional
        Scale parameters of the getRegion() function. Defaulting at ``20``,
        change it to change the scale of the final data points. The highest,
        the lower the spatial resolution. Should be at least ``10``.

    Returns
    -------
    `int`
        Returns the selected orbit number

    """
    orbit = ASCENDING if ascending else DESCENDING

    if top_left is not None:
        list_of_coordinates = [make_polygon(top_left, bottom_right)]
        polygon = ee.Geometry.Polygon(list_of_coordinates)
    else:
        if len(coords) == 2 and type(coords[0]) is not iterable:
            polygon = ee.Geometry.Point(coords)
        else:
            polygon = ee.Geometry.Polygon([coords])

    date_intervals = get_date_interval_array(start_date, end_date)

    sentinel_1_roi = filter_sentinel1_data(
        start_date=date_intervals[0][0],
        end_date=date_intervals[-1][1],
        geometry=polygon,
        orbit=orbit,
    )
    orbit_number_list = sentinel_1_roi.aggregate_array(
        "relativeOrbitNumber_start"
    ).getInfo()

    orbit_count = np.bincount(orbit_number_list, minlength=max(orbit_number_list))

    if orbit_number.lower() == "max":
        return np.argmax(orbit_count)
    if orbit_number.lower() == "min":
        orbit_count = np.ma.MaskedArray(orbit_count, orbit_count < 1)
        return np.ma.argmin(orbit_count)


def per_date_saving(
    save_dir: str,
    top_left=None,
    bottom_right=None,
    coords=None,
    start_date: datetime = date.today() - timedelta(days=365),
    end_date: datetime = date.today(),
    ascending: bool = True,
    orbit_number: object = None,
    scale: int = 20,
    n_jobs: int = 8,
    verbose: int = 1,
):
    """Fetches  & saves SAR data as GeoTIFFs

    Parameters
    ----------

    save_dir: str
        Path toward an *existing* directory where to save the images. If non-existing, an Exception is raised.

    top_left : tuple of float, optional
        Top left coordinates (lon, lat) of the Region

    bottom_right : tuple of float, optional
        Bottom right coordinates (lon, lat) of the Region

    coords : tuple of tuple of float or list of list of float, optional
        If `top_left` and `bottom_right` are not specified, we expect `coords`
        to be a list (resp. tuple) of the form ``[top_left, bottom_right]``
        (resp. ``(top_left, bottom_right)``)

    start_date : datetime.datetime, optional
        First date of the time interval

    end_date : datetime.datetime, optional
        Last date of the time interval

    ascending : boolean, optional
        The trajectory to use when selecting data

    orbit_number : int or str, optional
        The orbit number to restrict the download to. If provided with an integer, the S1 temporal stack is filtered using the provided orbit number.
        If provided with a string value, we expect one of these keywords:
         - "max" for the orbit number with the highest number of image in the stack
         - "min" for the orbit number with the smallest number of image in the stack
        If ``None``, then no filter over the orbit number is applied.

    scale : int, optional
        Scale parameters of the getRegion() function. Defaulting at ``20``,
        change it to change the scale of the final data points. The highest,
        the lower the spatial resolution. Should be at least ``10``.

    n_jobs : int, optional
        Set the parallelisation factor (number of threads) for the GEE data
        access process. Set to 1 if no parallelisation required.

    verbose : int, optional
        Verbosity mode (0: No info, 1: Info, 2: Detailed info, with added timestamp)

    Returns
    -------
    `dict`
        Dictionnary with four keys:

            ``"stack"``
                4-D array containing db intensity measure (`numpy.ndarray`),
                ``(height, width, pol_count, time_series_length)``

            ``"coordinates"``
                3-D array containg coordinates where ``[:,:,0]`` provides
                access to latitude and ``[:,:,1]`` provides access to
                longitude, (`numpy.ndarray`), ``(height, width, 2)``

            ``"timestamps"``
                list of acquisition timestamps of size (time_series_length,)
                (`list of str`)

            ``"metadata"``
                Dictionnary describing data for each axis of the stack and the
                coordinates
    """

    if save_dir is None or os.path.exists(save_dir) == False:
        raise ValueError(
            "Unknown directory. If you do not want to save data as geotiff files, please consider using the fetch method."
        )

    orbit = ASCENDING if ascending else DESCENDING
    if orbit_number is not None and type(orbit_number) == str:
        orbit_number = get_orbit_number(
            top_left,
            bottom_right,
            coords,
            start_date,
            end_date,
            ascending,
            orbit_number,
            scale,
        )

    if orbit_number is not None:
        print_verbose(f"Selected orbit: {orbit_number}", verbose, 1)

    list_of_coordinates = split_coordinates(
        top_left, bottom_right, coords, start_date, end_date, ascending, scale
    )

    date_intervals = get_date_interval_array(start_date, end_date)

    print_verbose(
        f"Region sliced in {len(list_of_coordinates)} subregions and {len(date_intervals)} time intervals.",
        verbose,
        1,
    )
    print_verbose(
        f"Generating values for each subcoordinate & sub-time intervals", verbose, 1
    )

    def single_date_saving(
        orbit, start_date, end_date, list_of_coordinates, save_dir, verbose: int = 0
    ):
        per_coord_dict = {}
        check_vals = False
        print_verbose(
            f"Starting process for interval {start_date}   {end_date}", verbose, 1
        )
        for n, c in enumerate(list_of_coordinates):
            vals = []
            headers = []
            polygon = ee.Geometry.Polygon([c])
            # Updates vals and headers, one by aggregating returned values of the delayed function, the other by modifying the passed `headers` argument
            vals = _get_zone_between_dates(
                start_date, end_date, polygon, scale, orbit, orbit_number, headers
            )
            properties = _get_properties_between_dates(
                start_date, end_date, polygon, orbit, orbit_number
            )
            if vals is not None:
                vals = [val for val in vals if val is not None]

                dictified_vals = [dict(zip(headers, values)) for values in vals]
                per_coord_dict = populate_coordinates_dictionary(
                    dictified_values=dictified_vals,
                    coordinates_dictionary={},
                )

                pixel_values = [per_coord_dict[k] for k in per_coord_dict.keys()]
                cmp_coordinates = cmp_to_key(cmp_coords)
                pixel_values.sort(
                    key=cmp_coordinates
                )  # sorting pixels by latitude then longitude

                timestamps = get_timestamps_from_pixel_values(pixel_values)
                img, coordinates = generate_image(
                    timestamps, pixel_values, properties, verbose=verbose
                )

                date = timestamps[0].strftime("%Y%m%d")
                print_verbose(f"Saving 't_{date}_{n}.tiff'", verbose, 2)

                save_as_geotiff(
                    os.path.join(save_dir, f"t_{date}_{n}.tiff"), img, coordinates
                )

                save_properties(f"t_{date}_{n}.json", properties)

                check_vals = True  # boolean variable to identify if an image exist in the checked time interval

        if check_vals:
            print_verbose(
                f"End process for interval {start_date}   {end_date}: image found & saved",
                verbose,
                1,
            )
        else:
            print_verbose(
                f"End process for interval {start_date}   {end_date}: No image found for this time interval",
                verbose,
                1,
            )

    Parallel(n_jobs=n_jobs)(
        delayed(single_date_saving)(
            orbit, sub_start_date, sub_end_date, list_of_coordinates, save_dir, verbose
        )
        for sub_start_date, sub_end_date in date_intervals
    )


def save_as_geotiff(filename, img, coordinates):
    """
    Saves the output of fetch methods as a geocoded TIFF file.

    Parameters
    ----------
    filename: str
        Name & path to save the GeoTIFF file

    img: numpy.ndarray
        4D Stack of SAR data with shape ``(height, width, pol_count, time_series_length)``

    coordinates: numpy.ndarray
        3-D array containg coordinates where ``[:,:,0]`` provides
        access to latitude and ``[:,:,1]`` provides access to
        longitude, (`numpy.ndarray`), ``(height, width, 2)``
    """
    try:
        from osgeo import gdal
        from osgeo import osr
    except Exception:
        raise ImportError(
            "GDAL does not seem to be installed on your system. Please make sure to install it using following this process: https://pypi.org/project/GDAL/"
        )

    head, tail = ntpath.split(filename)

    if head != "" and os.path.exists(head) == False:
        raise ValueError(
            "Path to save GeoTIFF unknown. Please verify that the saving directory exists on disk."
        )
    if tail.split(".")[-1] != "tif" and tail.split(".")[-1] != "tiff":
        raise ValueError(
            "Incorrect extension for GeoTIFF. Please either use .tif or .tiff"
        )

    if len(img.shape) == 4:
        img = img[:, :, :, 0]

    img_size = img.shape[0:2]
    # set geotransform
    nx = img_size[0]
    ny = img_size[1]
    xmin, ymin, xmax, ymax = [
        np.min(coordinates[:, :, 1]),
        np.min(coordinates[:, :, 0]),
        np.max(coordinates[:, :, 1]),
        np.max(coordinates[:, :, 0]),
    ]

    xres = (xmax - xmin) / float(ny)
    yres = (ymax - ymin) / float(nx)
    geotransform = (xmin, xres, 0, ymax, 0, -yres)

    # create the 3-band raster file
    dst_ds = gdal.GetDriverByName("GTiff").Create(filename, ny, nx, 2, gdal.GDT_Float32)

    dst_ds.SetGeoTransform(geotransform)  # specify coords
    srs = osr.SpatialReference()  # establish encoding
    srs.ImportFromEPSG(4326)  # WGS84 lat/long
    dst_ds.SetProjection(srs.ExportToWkt())  # export coords to file
    dst_ds.GetRasterBand(1).WriteArray(img[:, :, 0])  # write VV-band to the raster
    dst_ds.GetRasterBand(2).WriteArray(img[:, :, 1])  # write VH-band to the raster
    dst_ds.FlushCache()  # write to disk
    dst_ds = None


def save_properties(filename, properties):
    """
    Saves the output of fetch methods' properties as a .json file.

    Parameters
    ----------
    filename: str
        Name & path to save the GeoTIFF file

    properties: dict
        Properties dictionnary extracted alongside of

    """
    with open(filename, "w") as fout:
        json.dumps(properties, indent=4)