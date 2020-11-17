import math
from datetime import timedelta

MAX_GEE_PIXELS_DOWNLOAD = 1048576
GEE_ERROR_PLACEHOLDER = "ImageCollection.getRegion: Too many values: "

__all__ = ('tile_coordinates', 'retrieve_max_pixel_count_from_pattern',
           'cmp_coords', 'get_date_interval_array', 'make_polygon')


def make_polygon(top_left, bottom_right):
    '''Given two (lon, lat) coordinates of both the top left and bottom right corner of a polygon, return the list of corner coordinates of this polygon

    Parameters
    ----------
    top_left : list of int or tuple of int
        Top Left coordinates of the polygon
    bottom_right : list of int or tuple of int
        Bottom right coordinates of the polygon

    Returns
    -------
    list
        2-D list of the 5 coordinates need to create a Rectangular Polygon ``[top_left, top_right, bottom_right, bottom_left, top_left]``.
    '''
    return [
        list(top_left),
        [bottom_right[0], top_left[1]],
        list(bottom_right),
        [top_left[0], bottom_right[1]],
        list(top_left)
    ]


def tile_coordinates(total_count_of_pixels, coordinates, max_gee=MAX_GEE_PIXELS_DOWNLOAD):
    '''Given a coordinates array describing a Polygon, a count of pixes within that polygons, tiles this polygon into a grid a sub-Polygons where each sub-Polygon size matches the max_gee pixel count given as a parameter.

    Parameters
    ----------
    total_count_of_pixels : int
        Total number of pixels of the designated area
    coordinates : array of array of floats
        Can be a 5-sized list of every coordinates defining the polygon ``[[long1, lat1],[long2, lat1]...,[long1, lat1]]`` or a 2-sized list of coordinates defining the top left and bottom right corner of the Polygon ``[[long1, lat1],[long2, lat2]]``
    max_gee_threshold : int, optional
        Total number of points allowed for one data query. Default: 1048576

    Returns
    -------
    list
        3-dimensional list of coordinates with pixel count inferior or equal to the maximum GEE threshold (shape: ``(number of images, number of coordinates per image, 2)``)

    '''
    assert(len(coordinates) == 2 or len(coordinates) == 5)

    list_of_coordinates = []

    if len(coordinates) == 2:
        tmp_c = make_polygon(coordinates[0], coordinates[1])
    else:
        tmp_c = coordinates

    if (total_count_of_pixels < max_gee):
        return [tmp_c]

    # The coordinate polygon will be tiled in `grid_length * grid_length` sub-Polygons
    grid_length = int(math.ceil(math.sqrt(total_count_of_pixels/max_gee)))

    original_polygon_width = tmp_c[1][0] - tmp_c[0][0]
    original_polygon_height = tmp_c[3][1] - tmp_c[0][1]

    for i in range(grid_length):
        for j in range(grid_length):
            list_of_coordinates.append(
                make_polygon(
                    [tmp_c[0][0]+i*original_polygon_width/grid_length,
                        tmp_c[0][1]+j*original_polygon_height/grid_length], 
                    [tmp_c[0][0]+(i+1)*original_polygon_width/grid_length,
                        tmp_c[0][1]+(j+1)*original_polygon_height/grid_length]
                )
            )

    return list_of_coordinates


def retrieve_max_pixel_count_from_pattern(error_str):
    '''Given an input getRegion error from GEE, extract the provided points count.

    Parameters
    ----------
    error_str : str
        the str text of the GEE error (e.g. the function caled on ``"ImageCollection.getRegion: Too many values: x points ..."`` will output x)

    Returns
    -------
    int
        Returns the number of points specified in the input image
    '''
    try:
        return int(error_str.split("ImageCollection.getRegion: Too many values: ")[1].split(" points")[0])
    except:
        raise ValueError("No max pixels value found")


def cmp_coords(a, b):
    '''
    Given two coordinates dict a and b, compare which one is closer to the North-Eastern direction

    Parameters
    ----------
    a : dict 
        dict with keys ``"lon"`` and ``"lat"``
    b : dict
        dict with keys ``"lon"`` and ``"lat"``

    Returns
    -------
    int
        **-1** if ``a > b``, **1** if ``a < b``, **0** if ``a == b``
    '''
    if a["lat"] != b["lat"]:
        return 1 if a["lat"] < b["lat"] else -1
    elif a["lon"] != b["lon"]:
        return 1 if a["lon"] < b["lon"] else -1
    else:
        return 0


def define_image_shape(pixel_values):
    """Define image shape based on number pixel and latitude values

    Parameters
    ----------
    pixel_values :
        Dictionnary with retrieved pixel values along with latitude and
        longitude coordinates

    Returns
    -------
    (with, height) :
        A tuple with the width and height of the requested area of interest
    """
    # count pixels with common latitude until it changes to know the image width
    width = 1
    while pixel_values[width]["lat"] == pixel_values[0]["lat"]:
        width += 1
    # deduce the image height from its width
    height = len(pixel_values) // width
    return (width, height)


def get_date_interval_array(start_date, end_date, day_timedelta=1):
    '''Initialize a list of days interval of size ``day_timedelta`` iteratively created between ``start_date`` and ``end_date``.

    Parameters
    ----------
    start_date : datetime.datetime
        first date time of the array
    end_date : datetime.datetime
        last date of the array
    day_timedelta : int
        size, in days, of every interval
    '''
    assert(start_date is not None and end_date is not None and day_timedelta is not None)
    assert(start_date < end_date)
    assert(type(day_timedelta) == int)

    date_intervals = []

    tmp_date = start_date

    while tmp_date < end_date:
        date_intervals.append((tmp_date.strftime(
            "%Y-%m-%d"), (tmp_date + timedelta(days=day_timedelta)).strftime("%Y-%m-%d")))
        tmp_date += timedelta(days=day_timedelta)

    return date_intervals
