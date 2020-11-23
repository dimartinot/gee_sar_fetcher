GEE SAR Fetcher
===============

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

Usage
-----

Python Import
~~~~~~~~~~~~~

The main function of this library is the ``fetch`` function:

.. code:: python

   from geesarfetcher import fetch
   from datetime import date, timedelta

   fetch(
       top_left = [-104.77431630331856, 41.729889598264826], 
       bottom_right = [-104.65140675742012, 41.81515375846025],
       start_date = date.today()-timedelta(days=15),
       end_date = date.today(),
       ascending=False,
       scale=10,
       n_jobs=1
   ) # returns a dictionnary with access to the data through the 'stack' keyword and to its timestamps through the 'timestamps' keyword

To fetch over a single point, the process is similar to the difference that we use another function, called ``fetch_point`` and only provide a single coordinates tuple rather than either two or 5 tuples for the area query.

.. code:: python

   from geesarfetcher import fetcher
   from datetime import date, timedelta

   fetch_point(
      coords = [-104.88572453696113, 41.884778748257574],
      start_date = date.today()-timedelta(days=15),
      end_date = date.today(),
      ascending=False,
      scale=10
   )

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