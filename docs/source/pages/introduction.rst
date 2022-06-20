An easy-to-use Python library to download SAR GRD imagery from Google
Earth Engine.

Introduction
------------

Access Google’s multi-petabytes of SAR Imagery data from your python
code with *no dimension restraint*. Simply supply coordinates, a time
interval and obtain a stack of Sentinel-1 preprocessed PolSAR images.
This enables quick data analysis of GRD images to get better insights of
the temporal dimension in SAR data without having to bother with
essential but potentially time-consuming steps such as coregistration or
calibration.

Compatible with python 3.


Addition with version 0.3.3
---------------------------

The development of version 0.3.3 added two new functionalities to the library:
 - the ability to select the orbit number of the downloaded temporal stack. It can directly be supplied by the user, or the said user can supply a keyword "min" or "max" and the adequate orbit number will automatically be extracted, given the orbit type and coordinates.
 - the ability to retrieve metadata from the downloaded stack, one per temporal image.


Usage
-----

The library allows the user to retrieve GEE Sar data eiter over a rectangular area or over a single coordinates tuple.

Fetch data over an area
~~~~~~~~~~~~~~~~~~~~~~~

The function to call in order to retrieve data over an area is the ``fetch`` function:

.. code:: python

   from geesarfetcher import fetch
   from datetime import datetime, timedelta

   d = fetch(
      top_left=[-116.17556985040491, 60.527371254744246],
      bottom_right=[-116.1364310564596, 60.54425859382555],
      start_date=datetime(year=2021, month=5, day=20) - timedelta(days=365),
      end_date=datetime(year=2021, month=5, day=20),
      ascending=False,
      scale=10,
      orbit_number="max",
      verbose=2
   ) # returns a dictionnary with access to the data through the 'stack' keyword, to its timestamps through the 'timestamps' keyword, to pixels' coordinates with 'coordinates' key and to metadata with the 'metadata' key.

It returns a ``dict`` object with 4 keys:
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

Fetch data over an area and save as a GeoTIFF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The function to call in order to retrieve & save data over an area is the ``fetch_and_save`` function:

.. code:: python

   from geesarfetcher import fetch_and_save
   from datetime import datetime, timedelta

   fetch_and_save(
      save_dir = ".",
      top_left = [-104.77431630331856, 41.729889598264826],
      bottom_right = [-104.65140675742012, 41.81515375846025],
      start_date = datetime(2019, 6, 1),
      end_date = datetime(2019, 6, 3),
      ascending = False,
      scale = 10,
      orbit_number="max",
      n_jobs = 8,
      verbose = 2
   ) # saves each timestep of the multitemporal SAR image in the directory specified by the keyword 'save_dir'


It saves each timestep as a GeoTIFF file using the following naming pattern: 't_{date}_{subcoordinate_index}.tiff'. Metadata are saved as .json files following the same naming convention (i.e. 't_{date}_{subcoordinate_index}.json').

Subcoordinate indexes are generated when splitting the initial whole area into smaller areas. 
Each of the subregion is then saved as a separate GeoTIFF, for less memory consumption.
Every GeoTIFF contains in its first band VV values and in its second band VH values.

Fetch data for a single point
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To fetch over a single point, the process is similar to the difference that we use another function, called ``fetch_point`` and only provide a single coordinates tuple rather than either two or 5 tuples for the area query.

.. code:: python

   from geesarfetcher import fetch_point
   from datetime import date, timedelta

   d = fetch_point(
      coords = [-104.88572453696113, 41.884778748257574],
      start_date = date.today()-timedelta(days=15),
      end_date = date.today(),
      ascending = False,
      scale = 10,
      orbit_number="max",
      verbose = 2
   )

For data consistency, the returned object is of the same nature as with the ``fetch`` method, i.e a ``dict`` with 4 keys:
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

Installation
------------

Access to Google Earth Engine is conditioned by the obtention of a `GEE
account`_. Once created, you can install the **geesarfetcher** API and
register an identifying token for your Python working environment using
the following commands:

::

   pip install geesarfetcher
   earthengine authenticate

Contributing
------------

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change. Please make sure to update
tests as appropriate.

License
-------

`MIT`_

.. _GEE account: https://earthengine.google.com/
.. _MIT: https://choosealicense.com/licenses/mit/