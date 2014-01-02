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

from amondawa import util, config
from amondawa.dp_schema import DatapointsSchema
from amondawa.util import IndexKey

from boto import dynamodb2
from boto.dynamodb2.fields import HashKey, RangeKey
from boto.dynamodb2.table import Table
from boto.dynamodb2.types import *

from repoze.lru import LRUCache

import atexit

config = config.get()

class Schema(object):
  table_names = 'amdw_metric_names', 'amdw_tag_names', 'amdw_tag_values'

  metric_names_tp      = { 'read': 1, 'write': 1 }
  tag_names_tp         = { 'read': 1, 'write': 1 }
  tag_values_tp        = { 'read': 1, 'write': 1 }

  datapoints_lru = LRUCache(config.CACHE_DATAPOINTS)
  index_key_lru = LRUCache(config.CACHE_QUERY_INDEX_KEY)

  @staticmethod
  # TODO: deal with concurrent table operation limit (tables operations > 10)
  def delete(connection):
    """Destructive delete of schema and data.
    """
    for table in Schema.table_names:
      try:
        Table(table, connection=connection).delete()
      except: pass

    DatapointsSchema.delete(connection)

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
    Table.create('amdw_metric_names',
        schema = [ HashKey('domain'), RangeKey('name') ],
        throughput = Schema.metric_names_tp, connection=connection)
    Table.create('amdw_tag_names',
        schema = [ HashKey('domain'), RangeKey('name') ],
        throughput = Schema.tag_names_tp, connection=connection)
    Table.create('amdw_tag_values',
        schema = [ HashKey('domain'), RangeKey('value') ],
        throughput = Schema.tag_values_tp, connection=connection)

    DatapointsSchema.create(connection)

  def __init__(self, connection):
    """Initilize data structures.
    """
    self.connection = connection
    # TODO these should be LRU cache - this will become too large
    self.metric_name_cache = set()
    self.tag_name_cache = set()
    self.tag_value_cache = set()

    # use table names as var names
    vars(self).update(Schema.bind(connection))

    self.blocks = DatapointsSchema(connection)
    self.blocks.start_maintenance()

    @atexit.register
    def close():
      try:
        self.connection.close()
      except:
        pass # called on abruptly exit

  def close(self):
    """Close connection and flush pending operations.
    """
    self.connection.close()

  def get_metric_names(self, domain):
    """Get all metric names.
    """
    return [item['name'] for item in self.amdw_metric_names.query(consistent=False, 
      attributes=['name'], domain__eq=domain)]

  def get_tag_names(self, domain):
    """Get tag names.
    """
    return [item['name'] for item in self.amdw_tag_names.query(consistent=False, 
      attributes=['name'], domain__eq=domain)]

  def get_tag_values(self, domain):
    """Get all tag values.
    """
    return [item['value'] for item in self.amdw_tag_values.query(consistent=False, 
      attributes=['value'], domain__eq=domain)]

  def store_datapoint(self, timestamp, metric, tags, value, domain):
    """Store a single datapoint, adding to ancillary tables if required.  This call
        will buffer write operations into the provided writer before sending to
        dynamodb.
    """
    self._store_tags(domain, tags)
    self._store_metric(domain, metric)

    self.blocks.store_datapoint(timestamp, metric, tags, value, domain)

  def query_index(self, domain, metric, start_time, end_time):
    """Query index for keys.
    """
    return self.blocks.query_index(domain, metric, start_time, end_time)

  def query_datapoints(self, index_key, start_time, end_time, attributes=['value']):
    """Query datapoints.
    """
    return self.blocks.query_datapoints(index_key, start_time, end_time, attributes)

  def _store_cache(self, key, cache, table, data):
    if not key in cache:
      table.put_item(data=data(), overwrite=True)
      cache.add(key)

  def _store_tag_name(self, domain, name):
    """Store tag name if not yet stored.
    """
    self._store_cache('|'.join([domain, name]), self.tag_name_cache,
        self.amdw_tag_names, lambda: { 'domain': domain, 'name': name })
 
  def _store_tag_value(self, domain, value):
    """Store tag value if not yet stored.
    """
    self._store_cache('|'.join([domain, value]), self.tag_value_cache,
        self.amdw_tag_values, lambda: { 'domain': domain, 'value': value })
 
  def _store_metric(self, domain, metric):
    """Store metric name if not yet stored.
    """
    self._store_cache('|'.join([domain, metric]), self.metric_name_cache,
        self.amdw_metric_names, lambda: { 'domain': domain, 'name': metric })

  def _store_tags(self, domain, tags):
    """Store tags if not yet stored.
    """
    for name, value in tags.items():
      self._store_tag_name(domain, name)
      self._store_tag_value(domain, value)


