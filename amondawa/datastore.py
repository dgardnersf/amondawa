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
Classes for querying and storing datapoints.
"""

from amondawa import schema, util
from decimal import Decimal
from threading import Thread
import time

# rough time intervals
TIME_ITERVALS = {
  'milliseconds': 1, 
  'seconds':      1000, 
  'minutes':      1000*60, 
  'hours':        1000*60*60, 
  'days':         1000*60*60*24, 
  'weeks':        1000*60*60*24*7, 
  'months':       1000*60*60*24*30, 
  'years':        1000*60*60*24*365
}

class Datastore(object):
  """Object based access to the time series database.
  """
  def __init__(self, connection, domain='nodomain'):
    self.connection = connection

    tables = schema.bind(connection)

    self.index = tables['data-points-index']
    self.dp_table = tables['data-points']
    self.metric_names = tables['metric-names']
    self.tag_values = tables['tag-values']
    self.tag_names = tables['tag-names']

    self.dp_writer = self.dp_table.batch_write()
    self.domain = domain

  def put_data_points(self, dps):
    """Store elements of DataPointSet.
    """
    for dp in dps:
      schema.store_datapoint(self.dp_writer, self.index,
          dp.timestamp, dps.name, dps.tags, dp.value, self.domain)

  def get_metric_names(self):
    """Get the names of the metrics in the database.
    """
    return schema.get_metric_names(self.metric_names)

  def get_tag_names(self):
    """Get the names of the tags in the database.
    """
    return schema.get_tag_names(self.tag_names)

  def get_tag_values(self):
    """Get the values of the tags in the database.
    """
    return schema.get_tag_values(self.tag_values)

  def query_database(self, query, query_callback):
    """Query datapoints by time interval and tags.
    """
    # for each matching index key, create a datapoints query thread
    query_threads = []
    for index_key in self.__query_index_keys(query.name, query.start_time, 
        query.end_time, query.tags, self.domain):
      query_threads.append(QueryThread(self.dp_table, index_key, query.start_time, query.end_time))

    # start the query threads
    for query in query_threads:
      query.start()

    # join the threads (in same order) calling the callback
    tag_string = None
    for query in query_threads:
      if tag_string != query.get_tag_string():
        if tag_string:
          query_callback.end_datapoint_set()
        query_callback.start_datapoint_set(query.get_tags())
        tag_string = query.get_tag_string()
      for timestamp, value in query.get_result():
        query_callback.add_data_point(timestamp, value)

    if len(query_threads):
      query_callback.end_datapoint_set()

    return query_callback

  def query_metric_tags(self, query):
    """Query datapoint tags by time interval and tags.
    """
    # get index keys (domain_metric_tbase_tags)
    index_keys = self.__query_index_keys(query.name, 
        query.start_time, query.end_time, query.tags, self.domain)
    # convert tag part to kv pair dictionaries
    return util.to_multi_map([key.get_tags() for key in index_keys])

  def delete_data_points(self, delete_query):
    """Delete datapoints by time interval and tags.
    """
    pass

  def close(self):
    """Flush any cached state and close connections.
    """
    self.dp_writer.flush()
    self.connection.close()

  def __query_index_keys(self, metric, start_time, end_time, tags, domain):
    """Query index keys by time interval and tags.
    """
    return filter(lambda key: key.has_tags(tags),
        schema.query_index(self.index, domain, metric, start_time, end_time))


class SimpleQueryCallback(object):
  """A simple collector for results.
  """
  def __init__(self, name):
    self.name = name
    self.results = []
    self.sample_size = 0
    self.datapoints = self.current = None

  def start_datapoint_set(self, tags):
    self.datapoints = []
    self.current = {
      'name': self.name,
      'tags': tags,
      'values': self.datapoints
    }

  def add_data_point(self, *args):
    self.datapoints.append(args)

  def end_datapoint_set(self):
    self.sample_size += len(self.datapoints)
    if self.current:
      self.results.append(self.current)
    self.current = None


class QueryMetric(object):
  """DataPoint query class.
  """
  @staticmethod
  def from_json_object(json):
    """Factory method: query from json.
    """
    start, end = QueryMetric.__time_interval_from_json(json)
    return [QueryMetric(start, end, metric['name'], metric['tags']) \
      for metric in json['metrics']]

  @staticmethod
  def __calc_time(now, json, stend):
    """Calculate absolute time from absolute timestamp or relative time struct.
    """
    abs_str, rel_str = stend + '_absolute', \
        stend + '_relative'
    t = now
    if abs_str in json:
      t = int(json[abs_str])
    elif rel_str in json:
      relative = json[rel_str]
      t = now - int(relative['value']) * \
                TIME_ITERVALS[relative['unit']]
    return t

  @staticmethod
  def __time_interval_from_json(json):
    """Calculate absolute time from absolute timestamp or relative time struct.
    """
    now = int(round(time.time() * 1000))
    return (QueryMetric.__calc_time(now, json, stend) \
      for stend in ('start', 'end'))

  def __init__(self, start_time, end_time, name, tags=None, cache_time=0):
    self.start_time = start_time
    self.end_time = end_time
    self.cache_time = cache_time
    self.name = name
    self.tags = tags

  def add_tag(self, name, value):
    self.tags[name] = value

  def add_aggregator(self, aggregator): pass
  def add_group_by(self, group_by): pass
  def is_exclude_tags(self): pass
  def set_exclude_tags(self, exclude_tags): pass


class DataPoint(object):
  """A single datapoint.
  """
  def __init__(self, timestamp, value):
    self.timestamp = timestamp
    self.value = value

  def is_integer(self):
    return type(self.value) == int

  def __repr__(self):
    return str(self)

  def __str__(self):
		return "DataPoint{timestamp=%s, is_integer=%s, value=%s}" % \
        (self.timestamp, self.is_integer(), self.value)

  def __cmp__(self, o):
    ret = cmp(self.timestamp, o.timestamp)
    if not ret:
      return cmp(self.value, o.value)
    return ret

  def __hash__(self):
    ret = 17
    ret = 31*ret + hash(self.value)
    ret = 31*ret + hash(self.timestamp)
    return ret

  def __eq__(self, o):
    return self is o or (type(o) == DataPoint and \
      self.value == o.value and self.timestamp == o.timestamp)

class DataPointSet(list):
  """A collection of datapoints.
  """
  @staticmethod
  def from_json_object(json):
    """Factory method: datapoints from json.
    """
    ret = []
    for o in json:
      dps = DataPointSet(o['name'], o['tags'])
      if 'timestamp' in o:
        dps.append(DataPoint(o['timestamp'], Decimal(str(o['value']))))
      elif 'datapoints' in o:
        for timestamp, value in o['datapoints']:
          dps.append(DataPoint(timestamp, Decimal(str(value))))
      ret.append(dps)
    return ret

  def __init__(self, name, tags={}, data_points=[]):
    self.name = name
    self.tags = tags
    self.extend(data_points)

  def add_tag(self, name, value):
    self.tags[name] = value

  def __str__(self):
    return "DataPointSet{name='%s', tags=%s, data_points=%s}" % \
        (self.name, self.tags, super(DataPointSet, self).__str__())

  def __eq__(self, o):
    return self is o or (type(o) == DataPointSet and \
      self.data_points == o.data_points and \
      self.name == o.name and self.tags == o.tags)

class QueryThread(Thread):
  """A thread used to query the datapoints.
  """
  def __init__(self, dp_table, index_key, start_time, end_time):
    super(QueryThread, self).__init__()
    self.dp_table = dp_table
    self.index_key = index_key
    self.start_time, self.end_time = start_time, end_time

  def run(self):
    self.result = [(item['toffset'] + self.get_tbase(), item['value']) for item in \
      schema.query_datapoints(self.dp_table, self.index_key, self.start_time, 
        self.end_time)]

  def get_tbase(self):
    return self.index_key.get_tbase()

  def get_tag_string(self):
    return self.index_key.get_tag_string()

  def get_tags(self):
    return self.index_key.get_tags()

  def get_result(self):
    self.join()
    return self.result

