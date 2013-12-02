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

class Schema(object):
  table_names = 'data_points', 'data_points_index', 'metric_names', \
                'tag_names', 'tag_values'

  metric_names_tp = { 'read': 1, 'write': 1 }
  tag_names_tp = { 'read': 1, 'write': 1 }
  tag_values_tp = { 'read': 1, 'write': 1 }
  data_points_tp = { 'read': 10, 'write': 40 }
  data_points_index_tp = { 'read': 40, 'write': 1 }

  @staticmethod
  def delete(connection):
    """Destructive delete of schema and data.
    """
    for table in Schema.table_names:
      Table(table, connection=connection).delete()

  @staticmethod
  def bind(connection):
    """Bind to existing dynamodb tables.
    """
    return dict(((table, Table(table, connection=connection)) for table in \
                               Schema.table_names))

  @staticmethod
  def create(connection):
    """Create dynamodb tables.
    """
    Table.create('metric_names',
        schema = [ HashKey('domain'), RangeKey('name') ],
        throughput = Schema.metric_names_tp, connection=connection)
    Table.create('tag_names',
        schema = [ HashKey('domain'), RangeKey('name') ],
        throughput = Schema.tag_names_tp, connection=connection)
    Table.create('tag_values',
        schema = [ HashKey('domain'), RangeKey('value') ],
        throughput = Schema.tag_values_tp, connection=connection)
    Table.create('data_points',
        schema = [ HashKey('domain_metric_tbase_tags'),
          RangeKey('toffset', data_type=NUMBER) ],
        throughput = Schema.data_points_tp, connection=connection)
    Table.create('data_points_index',
        schema = [ HashKey('domain_metric'), RangeKey('tbase_tags') ],
        throughput = Schema.data_points_index_tp, connection=connection)

  def __init__(self, connection):
    """Initilize data structures.
    """
    self.index_key_cache = set()
    self.metric_name_cache = set()
    self.tag_name_cache = set()
    self.tag_value_cache = set()

    # use table names as var names
    vars(self).update(Schema.bind(connection))

    self.dp_writer = self.data_points.batch_write()

  def close(self):
    """Close connection and flush pending operations.
    """
    self.dp_writer.flush()
    self.connection.close()

  def get_metric_names(self, domain):
    """Get all metric names.
    """
    return [item['name'] for item in self.metric_names.query(consistent=False, 
      attributes=['name'], domain__eq=domain)]

  def get_tag_names(self, domain):
    """Get tag names.
    """
    return [item['name'] for item in self.tag_names.query(consistent=False, 
      attributes=['name'], domain__eq=domain)]

  def get_tag_values(self, domain):
    """Get all tag values.
    """
    return [item['value'] for item in self.tag_values.query(consistent=False, 
      attributes=['value'], domain__eq=domain)]

  def store_datapoint(self, timestamp, metric, tags, value, domain):
    """Store a single datapoint, adding to ancillary tables if required.  This call
        will buffer write operations into the provided writer before sending to
        dynamodb.
    """
    key = util.hdata_points_key(domain, metric, timestamp, tags)
    self.__store_index(key, timestamp, metric, tags, domain)
    self.__store_tags(domain, tags)
    self.__store_metric(domain, metric)

    self.dp_writer.put_item(data = {
      'domain_metric_tbase_tags': key,
      'toffset': util.offset_time(timestamp),
      'value': value
      })
  
  def query_index(self, domain, metric, start_time, end_time):
    """Query index for keys.
    """
    return [IndexKey(k) for k in self.data_points_index.query(consistent=True, 
      domain_metric__eq=util.index_hash_key(domain, metric), 
      tbase_tags__between=[str(util.base_time(v)) for v in (start_time, end_time)])]

  def query_datapoints(self, index_key, start_time, end_time, attributes=['value']):
    """Query datapoints.
    """
    return self.data_points.query(consistent=False, 
      reverse=True, attributes=['toffset'] + attributes, 
      domain_metric_tbase_tags__eq=index_key.to_data_points_key(), 
      toffset__between=util.offset_range(index_key, start_time, end_time))

  def __store_cache(self, key, cache, table, data):
    if not key in cache:
      table.put_item(data=data(), overwrite=True)
      cache.add(key)

  def __store_index(self, key, timestamp, metric, tags, domain):
    """Store an index key if not yet stored.
    """
    self.__store_cache(key, self.index_key_cache, self.data_points_index,
        lambda: { 'domain_metric': util.index_hash_key(domain, metric),
          'tbase_tags': util.index_range_key(timestamp, tags) })

  def __store_tag_name(self, domain, name):
    """Store tag name if not yet stored.
    """
    self.__store_cache('|'.join([domain, name]), self.tag_name_cache, self.tag_names,
        lambda: { 'domain': domain, 'name': name })
 
  def __store_tag_value(self, domain, value):
    """Store tag value if not yet stored.
    """
    self.__store_cache('|'.join([domain, value]), self.tag_value_cache, self.tag_values,
        lambda: { 'domain': domain, 'value': value })
 
  def __store_metric(self, domain, metric):
    """Store metric name if not yet stored.
    """
    self.__store_cache('|'.join([domain, metric]), self.metric_name_cache, self.metric_names,
        lambda: { 'domain': domain, 'name': metric })

  def __store_tags(self, domain, tags):
    """Store tags if not yet stored.
    """
    for name, value in tags.items():
      self.__store_tag_name(domain, name)
      self.__store_tag_value(domain, value)

