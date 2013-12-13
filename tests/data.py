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

import string

def rot_zip_str(a, b):
  return ['%s%s' % (a[i % len(a)], b[i % len(b)]) for i in range(max(len(a), len(b)))]

# domainA, domainB, ... domainZ
all_domains = rot_zip_str(['domain'], string.ascii_uppercase)

all_metrics = {
# 'name':      [min, max]
  'rpo':       [10, 750],
  'cpu_util':  [0, 100],
  'disk_free': [0, 10*1024*1024],
  'birds_free': [0, 10*1024*1024],
  'free_birds': [0, 10*1024*1024],
  'bytes_in':  [0, 1024*1024],
  'bytes_out': [0, 1024*1024]
}

all_tags = {
  'match':     ['bbbbb','rrrr', '1889', 'tagtagtag'],
  'type':      ['storage', 'network', 'compute', 'time', 'space'],
  'host':      ['10.0.0.1', '10.2.2.1', '10.0.0.2', '172.4.5.1'],
  'name':      ['aaaa40', 'dan', 'bbbb56', 'consistent'],
  'protected': ['protected', 'infrastructure', 'blah'],
  'group':     ['group1', 'group2', 'group3', 'group4']
}
