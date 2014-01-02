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

from boto.dynamodb2.fields import HashKey, RangeKey
from boto.dynamodb2.table import Table
from boto.dynamodb2.types import *

import amondawa, os, sys, time

MAX_WAIT = 120

REGION = os.environ.get('AMDW_REGION', 'us-west-2')

connection = amondawa.connect(REGION)

config_table = Table('amdw_config', connection=connection)
desc = None
try:
  desc = config_table.describe()
except:
  config_table = Table.create('amdw_config',
        schema = [ HashKey('name') ],
        throughput = { 'read': 1, 'write': 1 }, connection=connection)

desc = config_table.describe()
while MAX_WAIT and desc['Table']['TableStatus'] != 'ACTIVE':
  MAX_WAIT -= 1
  time.sleep(1)
  desc = config_table.describe()

if desc['Table']['TableStatus'] != 'ACTIVE':
  print 'error accessing amdw_config table in region', region
  sys.exit(1)

config = None

class configuration(object):
  def __init__(self, config_table):
    vars(self).update(dict((item['name'].upper(), item['value']) \
        for item in config_table.scan()))

def get():
  return config

def refresh():
  global config
  config = configuration(config_table)
  return config

def write(configuration):
  for name, value in configuration.items():
    config_table.put_item({'name': name, 'value': value}, overwrite=True)


refresh()
