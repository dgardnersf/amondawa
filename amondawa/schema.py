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
Classes dealing directly with the dynamodb schema.
"""
from boto import dynamodb2
from boto.dynamodb2.fields import HashKey, RangeKey
from boto.dynamodb2.table import Table
from boto.dynamodb2.types import *

from amondawa import util
from amondawa.util import IndexKey

index_key_cache = set()
metric_name_cache = set()
tag_name_cache = set()
tag_value_cache = set()

table_names = 'data-points', 'data-points-index', 'metric-names', 'tag-names', 'tag-values'

def delete_schema(connection):
  """Destructive delete of schema and data.
  """
  for table in table_names:
    Table(table, connection=connection).delete()

def bind(connection):
  """Bind to existing dynamodb tables.
  """
  return dict(((table, Table(table, connection=connection)) for table in table_names))

def create_schema(connection):
  """Create dynamodb tables.
  """
  Table.create('metric-names', 
      schema = [ HashKey('domain'), RangeKey('name') ], 
      throughput = { 'read': 1, 'write': 1, }, connection=connection)
  Table.create('tag-names', 
      schema = [ HashKey('domain'), RangeKey('name') ], 
      throughput = { 'read': 1, 'write': 1, }, connection=connection)
  Table.create('tag-values', 
      schema = [ HashKey('domain'), RangeKey('value') ], 
      throughput = { 'read': 1, 'write': 1, }, connection=connection)
  Table.create('data-points', 
      schema = [ HashKey('domain_metric_tbase_tags'), 
        RangeKey('toffset', data_type=NUMBER) ], 
      throughput = { 'read': 10, 'write': 40, }, connection=connection)
  Table.create('data-points-index', 
      schema = [ HashKey('domain_metric'), RangeKey('tbase_tags') ], 
      throughput = { 'read': 40, 'write': 1, }, connection=connection)

def get_metric_names(table):
  """Get all metric names.
  """
  return table.scan()

def get_tag_names(table):
  """Get tag names.
  """
  return table.scan()

def get_tag_values(table):
  """Get all tag values.
  """
  return table.scan()

def store_datapoint(dp_writer, index, timestamp, metric, tags, value, domain):
  """Store a single datapoint, adding to ancillary tables if required.  This call
      will buffer write operations into the provided writer before sending to
      dynamodb.
  """
  key = util.hdata_points_key(domain, metric, timestamp, tags)
  if not key in index_key_cache:
    store_index(index, timestamp, metric, tags, domain)
    index_key_cache.add(key)
  dp_writer.put_item(data = {
    'domain_metric_tbase_tags': key,
    'toffset': util.offset_time(timestamp),
    'value': value
    })

def store_index(index, timestamp, metric, tags, domain):
  """Store an index key.
  """
  index.put_item(data = {
    'domain_metric': util.index_hash_key(domain, metric),
    'tbase_tags': util.index_range_key(timestamp, tags)
  }, overwrite=True)

def query_index(index, domain, metric, start_time, end_time):
  """Query index for keys.
  """
  print '>>>>>>>>>>>>', index, domain, metric, start_time, end_time
  return [IndexKey(k) for k in index.query(consistent=True, 
    domain_metric__eq=util.index_hash_key(domain, metric), 
    tbase_tags__between=[str(util.base_time(v)) for v in (start_time, end_time)])]

def query_datapoints(dp_table, index_key, start_time, end_time, attributes=['value']):
  """Query datapoints.
  """
  print '>>>>>>>>>>>>', dp_table, index_key, start_time,  end_time, attributes
  return dp_table.query(consistent=False, 
    reverse=True, attributes=['toffset'] + attributes, 
    domain_metric_tbase_tags__eq=index_key.to_data_points_key(), 
    toffset__between=util.offset_range(index_key, start_time, end_time))

