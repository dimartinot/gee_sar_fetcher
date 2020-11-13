#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
from setuptools import setup, find_packages
import itertools
# read the contents of your README file
from os import path
this_directory = path.abspath(path.dirname(__file__))

# Parse the version from the geextract module.
with open('geesarfetcher/__init__.py') as f:
    for line in f:
        if line.find("__version__") >= 0:
            version = line.split("=")[1].strip()
            version = version.strip('"')
            version = version.strip("'")
            continue

# 
extra_reqs = {'docs': ['sphinx',
                       'sphinx-rtd-theme',
                       'sphinxcontrib-programoutput']}
extra_reqs['all'] = list(set(itertools.chain(*extra_reqs.values())))

with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    readme = f.read()
    
setup(name='geesarfetcher',
      version=version,
      description=u"Extract Sentinel-1 GRD time-series images over a given area from google earth engine",
      long_description=readme,
      long_description_content_type="text/markdown",
      classifiers=[],
      keywords='SAR, sentinel, google, gee, time-series, radar, satellite imagery',
      author=u"Thomas Di Martino",
      author_email='thomas.di-martino@hotmail.com',
      url='https://github.com/dimartinot/gee_sar_fetcher',
      license='MIT',
      packages=find_packages(),
      install_requires=[
          'tqdm>=4.50.2',
          'numpy>=1.18.0,<=1.19.3',
          'earthengine-api>=0.1.231',
          'joblib>=0.17.0'],
      #scripts=['geextract/scripts/gee_extract.py',
      #         'geextract/scripts/gee_extract_batch.py'],
      test_suite="tests",
      extras_require=extra_reqs)
