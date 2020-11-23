"""geesarfetcher"""

__version__ = "0.2.0"

# LIBRARY IMPORTS
import ee
import warnings
from datetime import datetime, date, timedelta
import os

# LOCAL IMPORTS
from .api import generate_image
from .api import get_pixel_values
from .api import get_point_pixel_values
from .api import get_timestamps_from_pixel_values
from .assertions import _fetch_assertions
from .assertions import _fetch_point_assertions


warnings.simplefilter(action="ignore")
warnings.filterwarnings('ignore')

if os.environ.get('READTHEDOCS') == None:
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

    n_jobs : int, optional
        Set the parallelisation factor (number of threads) for the GEE data
        access process. Set to 1 if no parallelisation required.

    Returns
    -------
    `dict`
        Dictionnary with four keys:

            ``"stacks"``
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
    '''

    _fetch_assertions(top_left, bottom_right, coords, start_date, end_date, ascending, scale, n_jobs)    

    pixel_values = get_pixel_values(top_left=top_left, bottom_right=bottom_right, coords=coords, start_date=start_date, end_date=end_date, ascending=ascending, scale=scale, n_jobs=n_jobs)
    timestamps = get_timestamps_from_pixel_values(pixel_values)
    img, coordinates = generate_image(timestamps, pixel_values)

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

def fetch_point(
    coords,
    start_date: datetime = date.today()-timedelta(days=365),
    end_date: datetime = date.today(),
    ascending: bool = True,
    scale: int = 20,
    n_jobs: int = 8
):
    '''Fetches SAR data from a single coordinate point in the form of a dictionnary with image data as well as timestamps

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
    `dict`
        Dictionnary with four keys:

            ``"stacks"``
                4-D array containing db intensity measure (`numpy.ndarray`),
               ``(1, 1, pol_count, time_series_length)`` 

            ``"coordinates"``
                3-D array containg coordinates where ``[:,:,0]`` provides
                access to latitude and ``[:,:,1]`` provides access to
                longitude, (`numpy.ndarray`), ``(1, 1, 2)``

            ``"timestamps"``
                list of acquisition timestamps of size (time_series_length,)
                (`list of str`)

            ``"metadata"``
                Dictionnary describing data for each axis of the stack and the
                coordinates
                
    '''

    _fetch_point_assertions(coords, start_date, end_date, ascending, scale, n_jobs)

    pixel_values = get_point_pixel_values(coords=coords, start_date=start_date, end_date=end_date, ascending=ascending, scale=scale, n_jobs=n_jobs)
    timestamps = get_timestamps_from_pixel_values(pixel_values)
    img, coordinates = generate_image(timestamps, pixel_values)

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