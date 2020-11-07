# GEE SAR Fetcher
An easy-to-use Python library to download SAR GRD imagery from Google Earth Engine.

## Introduction
Access Google's multi-petabytes of SAR Imagery data from your python code with *no dimension restraint*. Simply supply coordinates, a time interval and obtain a stack of Sentinel-1 preprocessed PolSAR images.
This enables quick data analysis of GRD images to get better insights of the temporal dimension in SAR data without having to bother with essential but potentially time-consuming steps such as coregistration or calibration. 

Compatible with python 3.

[![Documentation Status](https://readthedocs.org/projects/gee-sar-fetcher/badge/?version=latest)](https://gee-sar-fetcher.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://badge.fury.io/py/geesarfetcher.svg)](https://badge.fury.io/py/geesarfetcher)

## Usage
### Python Import
The main function of this library is the ``fetch`` function:
```python
from geesarfetcher import fetcher
from datetime import date, timedelta

fetch(
    top_left = [-104.77431630331856, 41.729889598264826], 
    bottom_right = [-104.65140675742012, 41.81515375846025],
    start_date = date.today()-timedelta(days=15),
    end_date = date.today(),
    ascending=False
) # returns a dictionnary with access to the data through the 'stack' keyword and to its timestamps through the 'timestamps' keyword

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
