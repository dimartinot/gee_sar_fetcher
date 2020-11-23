from geesarfetcher import fetch, fetch_point
import unittest
import numpy as np
from datetime import datetime, date, timedelta
import warnings
warnings.simplefilter(action="ignore")

# SMALL COORDS
SMALL_COORDS = [
    [-104.71539380321867, 41.77751907620989],
    [-104.7079050756491, 41.77751907620989],
    [-104.7079050756491, 41.78321546046257],
    [-104.71539380321867, 41.78321546046257],
    [-104.71539380321867, 41.77751907620989]
]

MED_COORDS = [
    [-104.77431630331856, 41.729889598264826],
    [-104.65140675742012, 41.729889598264826],
    [-104.65140675742012, 41.81515375846025],
    [-104.77431630331856, 41.81515375846025],
    [-104.77431630331856, 41.729889598264826]
]

BIG_COORDS = [
    [-104.88572453696113, 41.62148183942426],
    [-104.53690861899238, 41.62148183942426],
    [-104.53690861899238, 41.884778748257574],
    [-104.88572453696113, 41.884778748257574],
    [-104.88572453696113, 41.62148183942426]
]


class TestFetcher(unittest.TestCase):
    def test_small_download(self):
        '''Tests download with a small region and small time interval
        '''
        d = fetch(
            top_left=SMALL_COORDS[0],
            bottom_right=SMALL_COORDS[2],
            start_date=datetime(year=2020, month=10, day=24),
            end_date=datetime(year=2020, month=11, day=2),
            ascending=False,
            scale=10)

        self.assertTrue(isinstance(d, dict))
        self.assertTrue("timestamps" in list(d.keys())
                        and len(d["timestamps"]) == 2)
        self.assertTrue(d["stack"].shape == (64, 83, 2, 2))

    def test_medium_download(self):
        '''Tests download with a medium region (at least one cut) and small time interval
        '''
        d = fetch(
            top_left=MED_COORDS[0],
            bottom_right=MED_COORDS[2],
            start_date=datetime(year=2020, month=10, day=24),
            end_date=datetime(year=2020, month=11, day=2),
            ascending=False,
            scale=10)

        self.assertTrue(isinstance(d, dict))
        self.assertTrue("timestamps" in list(d.keys())
                        and len(d["timestamps"]) == 2)
        self.assertTrue(d["stack"].shape == (949, 1368, 2, 2))

    def test_big_scale_download(self):
        '''Tests download with a large scale and missing pixel values
        '''
        d = fetch(
            top_left = [5.26948161, 49.97440374],
            bottom_right = [8.07913236, 47.90621773],
            start_date = datetime(2019, 6, 1),
            end_date = datetime(2019, 6, 3),
            ascending=False,
            scale=1000,
        )
        self.assertEqual(d["stack"].shape, (231, 312, 2, 1))
        self.assertEqual(d["stack"][100,100,0,0], -11.805720298590167)

    def test_fetch_point_small_scale(self):
        '''Tests fetch_point method with a relative small scale of 10
        '''
        d = fetch_point(
            coords = [-104.88572453696113, 41.884778748257574],
            start_date=datetime(year=2020, month=10, day=24),
            end_date=datetime(year=2020, month=11, day=2),
            ascending=False,
            scale=10
        )
        self.assertTrue(d['stack'].shape == (1,1,2,2))
        self.assertTrue(np.round(d['stack'][0,0,0,0] - (-15.11937733), 2) == 0.0)

    def test_fetch_point_med_scale(self):
        '''Tests fetch_point method with a relative medium scale of 100
        '''
        d = fetch_point(
            coords = [-104.88572453696113, 41.884778748257574],
            start_date=datetime(year=2020, month=10, day=24),
            end_date=datetime(year=2020, month=11, day=2),
            ascending=False,
            scale=100
        )
        self.assertTrue(d['stack'].shape == (1,1,2,2))
        self.assertTrue(np.round(d['stack'][0,0,0,0] - (-15.04562971), 2) == 0.0)

    def test_fetch_point_med_scale(self):
        '''Tests fetch_point method with a relative medium scale of 100
        '''
        d = fetch_point(
            coords = [-104.88572453696113, 41.884778748257574],
            start_date=datetime(year=2020, month=10, day=24),
            end_date=datetime(year=2020, month=11, day=2),
            ascending=False,
            scale=1000
        )
        self.assertTrue(d['stack'].shape == (1,1,2,2))
        self.assertTrue(np.round(d['stack'][0,0,0,0] - (-13.21006906), 2) == 0.0)

    def test_exceptions(self):
        '''Tests raised exceptions
        '''
        # Redundant information provided as input
        kwargs = {
            "top_left": MED_COORDS[0],
            "bottom_right": MED_COORDS[2],
            "coords": [MED_COORDS[0],MED_COORDS[2]],
            "start_date": datetime(year=2020, month=10, day=24),
            "end_date": datetime(year=2020, month=11, day=2),
            "ascending": False,
            "scale": 10
        }
        self.assertRaises(ValueError, fetch, **kwargs)

        # No coordinates provided
        kwargs["top_left"] = kwargs["bottom_right"] = kwargs["coords"] = None
        self.assertRaises(ValueError, fetch, **kwargs)

        # Only one coordinate provided
        kwargs["top_left"] = [0.0, 0.0]
        self.assertRaises(AssertionError, fetch, **kwargs)

        # Missing start date provided
        kwargs["top_left"] = MED_COORDS[0]
        kwargs["bottom_right"] = MED_COORDS[2]
        kwargs["start_date"] = None
        self.assertRaises(AssertionError, fetch, **kwargs)

        # Missing end date provided
        kwargs["start_date"] = datetime(year=2020, month=8, day=16)
        kwargs["end_date"] = None
        self.assertRaises(AssertionError, fetch, **kwargs)
        
