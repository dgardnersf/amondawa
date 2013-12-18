# Copyright (c) 2013 Daniel Gardner
# All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""
  Test data.
"""

import string

def rot_zip_str(a, b):
  return ['%s%s' % (a[i % len(a)], b[i % len(b)]) for i in range(max(len(a), len(b)))]

# domainA, domainB, ... domainZ
all_domains = rot_zip_str(['domain'], string.ascii_uppercase)

all_metrics = {
    'rpo':       {
      'range': [10, 750],
      'units': 'Minutes',
      'ylabel': 'RPO',
      'color_map': 'summer',
      'title': 'Recovery Point Objective'
      },
    'cpu_util':   {
      'range': [0, 100],
      'units': 'pct',
      'ylabel': 'util',
      'color_map': 'Greens',
      'title': 'CPU Utilization'
      },
    'disk_free':  {
      'range': [0, 10*1024*1024],
      'units':  'bytes',
      'ylabel': 'free',
      'color_map': 'spring',
      'title': 'Disk Free'
      },
    'dolphins':  {
      'range': [0, 10*1024*1024],
      'units': 'count',
      'ylabel': 'dolphins',
      'color_map': 'Blues',
      'title': 'Dolphins'
      },
    'free_birds':  {
      'range': [0, 10*1024*1024],
      'units': 'count',
      'ylabel': 'birds',
      'color_map': 'Reds',
      'title': 'Free Birds'
      },
    'bytes_in':   {
      'range': [0, 1024*1024],
      'units': 'bytes',
      'ylabel': 'in',
      'color_map': 'winter',
      'title': 'Bytes In'
      },
    'bytes_out':  {
      'range': [0, 1024*1024],
      'units': 'bytes',
      'color_map': 'Oranges',
      'ylabel': 'out',
      'title': 'Bytes Out'
      }
}

all_tags = {
  'match':     [8*'a',8*'b', 8*'c', 8*'d'],
  'type':      ['storage', 'network', 'compute', 'time', 'space'],
  'host':      ['10.0.0.1', '10.2.2.1', '10.0.0.2', '172.4.5.1'],
  'name':      ['chitta', 'jeff', 'venka', 'werner', 'jack'],
  'protected': ['protected', 'infrastructure', 'shared'],
  'group':     ['group1', 'group2', 'group3', 'group4']
}
