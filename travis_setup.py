#!/usr/bin/env python

import os
key = os.environ['GEE_API_KEY']
line = '{"refresh_token": "%s"}' % key
os.makedirs(os.path.expanduser('~/.config/earthengine/'))
with open(os.path.expanduser('~/.config/earthengine/credentials'), 'w') as dst:
   dst.write(line)

