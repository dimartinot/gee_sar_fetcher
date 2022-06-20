# GEE SAR Fetcher

An easy-to-use Python library to download SAR GRD imagery from Google Earth Engine.

---

## Additions with version 0.3.3

The development of version 0.3.3 added two new functionalities to the library:

- the ability to select the orbit number of the downloaded temporal stack. It can directly be supplied by the user, or the said user can supply a keyword "min" or "max" and the adequate orbit number will automatically be extracted, given the orbit type and coordinates.
- the ability to retrieve metadata from the downloaded stack, one per temporal image.

---

## Introduction

Access Google's multi-petabytes of SAR Imagery data from your python code with _no dimension restraint_. Simply supply coordinates, a time interval and obtain a stack of Sentinel-1 preprocessed PolSAR images.
This enables quick data analysis of GRD images to get better insights of the temporal dimension in SAR data without having to bother with essential but potentially time-consuming steps such as coregistration or calibration.

Compatible with python 3.

[![Documentation Status](https://readthedocs.org/projects/gee-sar-fetcher/badge/?version=latest)](https://gee-sar-fetcher.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://badge.fury.io/py/geesarfetcher.svg)](https://badge.fury.io/py/geesarfetcher)
[![Downloads](https://pepy.tech/badge/geesarfetcher)](https://pepy.tech/project/geesarfetcher)

## Usage

### Retrieve multitemporal SAR Images

The main function of this library is the `fetch` function:

```python
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
   ) # returns a dictionnary with access to the data through the 'stack' keyword and to its timestamps through the 'timestamps' keyword

```

### Retrieve multitemporal SAR Image and saves it as geocoded TIFFs

The fetch method loads the full data stack in memory. For large areas or long time interval, using the `fetch_and_save` alternative, that progressively saves SAR Images as GeoTIFF. They can then be opened in any QGIS-like software as a normal geocoded .tiff file. For more info, see [link...](https://gee-sar-fetcher.readthedocs.io/en/latest/pages/documentation.html#geesarfetcher.fetch_and_save)

```python
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
)
```

### Retrieve a single point SAR temporal signature

To fetch over a single point, the process is similar to the difference that we use another function, called `fetch_point` and only provide a single coordinates tuple rather than either two or 5 tuples for the area query.

```python
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
```

## Installation

Access to Google Earth Engine is conditioned by the obtention of a [GEE account](https://earthengine.google.com/).
Once created, you can install the **geesarfetcher** API and register an identifying token for your Python working environment using the following commands:

```
pip install geesarfetcher
earthengine authenticate
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
