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

from boto.dynamodb2.fields import HashKey
from boto.dynamodb2.table import Table

import amondawa
import os
import sys
import time

MAX_WAIT = 120

REGION = os.environ.get('AMDW_REGION', 'us-west-2')
TABLE_SPACE = os.environ.get('AMDW_TABLE_SPACE', 'amdw')

connection = amondawa.connect(REGION)

def table_name(table):
    """Return the name of the table give it's base name.

    @param table: the base name of the table.
    @return: the full name of the table
    """
    return '%s_%s' % (TABLE_SPACE, table)


def table_names(tables):
    """Given a list of table base names, return a dictionary
       mapping from base name to full name.

    @param tables: a list of base table names.
    @return: a dictionary mapping from base bame to full name.
    """
    return dict(map(lambda name: (name, table_name(name)), tables))

config_table = Table(table_name('config'), connection=connection)
desc = None
try:
    desc = config_table.describe()
except:
    config_table = Table.create(table_name('config'),
                                schema=[HashKey('name')],
                                throughput={'read': 1, 'write': 1}, connection=connection)

desc = config_table.describe()
while MAX_WAIT and desc['Table']['TableStatus'] != 'ACTIVE':
    MAX_WAIT -= 1
    time.sleep(1)
    desc = config_table.describe()

if desc['Table']['TableStatus'] != 'ACTIVE':
    print 'error accessing', table_name('config'), 'table in region', REGION
    sys.exit(1)

config = None


class Configuration(object):
    def __init__(self, config_table):
        vars(self).update(dict((item['name'].upper(), item['value']) \
                               for item in config_table.scan()))


def get():
    return config


def refresh():
    global config
    config = Configuration(config_table)
    return config


def write(configuration):
    for name, value in configuration.items():
        config_table.put_item({'name': name, 'value': value}, overwrite=True)


refresh()
