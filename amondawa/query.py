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
Classes for querying datapoints.
"""

# TODO rework threading using a pool - spawning endless threads won't scale

import pandas as pd
import numpy as np
from pandas.tseries import frequencies as freq
from threading import Thread

# rough time intervals
FREQ_MILLIS = {
  'milliseconds': 1, 
  'seconds':      1000, 
  'minutes':      1000*60, 
  'hours':        1000*60*60, 
  'days':         1000*60*60*24, 
  'weeks':        1000*60*60*24*7, 
  'months':       1000*60*60*24*30, 
  'years':        1000*60*60*24*365
}

FREQ_TYPE = {
  'milliseconds': freq.Milli(),
  'seconds':      freq.Second(),
  'minutes':      freq.Minute(),
  'hours':        freq.Hour(),
  'days':         freq.Day(),
  'weeks':        freq.Week(),
  'months':       freq.Day(30),
  'years':        freq.Day(365)
}

AGGREGATORS = { 
  'avg': np.mean,
  'dev': np.std,
  'div': None,
  'histogram': None,
  'least_squares': None,
  'max': np.max,
  'min': np.min,
  'rate': None,
  'sum': np.sum
}

class SimpleQueryCallback(object):
  """A simple collector for results.
  """
  def __init__(self, metric):
    self.metric = metric
    self.results = []
    self.sample_size = 0
    self.datapoints = self.current = None

  def start_datapoint_set(self, tags):
    self.datapoints = []
    self.current = {
      'name': self.metric,
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


class ResampleQueryCallback(object):
  """A resampling collector for results.
  """
  def __init__(self, metric, how, value, unit):
    self.metric = metric
    self.how = AGGREGATORS[how]          # TODO: check, raise exception here
    self.rule = value * FREQ_TYPE[unit]  # TODO: check, raise exception here
    self.results = []
    self.sample_size = 0
    self.index = self.values = None

  def start_datapoint_set(self, tags):
    self.index = []
    self.values = []
    self.current = {
      'name': self.metric,
      'tags': tags,
      'values': None
    }

  def _calculate(self):
    series = pd.Series(self.values, pd.to_datetime(self.index, unit='ms'))
    series = series.resample(self.rule, self.how)
    timestamps = [int(round(dt.value/1e6)) for dt in series.index]
    return zip(timestamps, series.values)

  def add_data_point(self, timestamp, value):
    self.index.append(timestamp)
    self.values.append(value)

  def end_datapoint_set(self):
    if self.current:
      self.current['values'] = self._calculate()
      self.results.append(self.current)
    self.sample_size += len(self.index)
    self.current = None


class GatherThread(Thread):
  """IO thread to read multiple query results and serialize together.
  """
  def __init__(self, query_threads, query_callback):
    super(GatherThread, self).__init__()
    self.query_callback = query_callback
    self.query_threads = query_threads

  def run(self):
    """
    """
    # join the query threads (in same order) calling the callback
    tag_string = None
    for query in self.query_threads:
      if tag_string != query.get_tag_string():
        if tag_string:
          self.query_callback.end_datapoint_set()
        self.query_callback.start_datapoint_set(query.get_tags())
        tag_string = query.get_tag_string()
      for timestamp, value in query.get_result():
        self.query_callback.add_data_point(int(timestamp), float(value))

    if len(self.query_threads):
      self.query_callback.end_datapoint_set()

  def get_result(self):
    self.join()
    return self.query_callback


class QueryThread(Thread):
  """A thread used to query the datapoints.
  """
  def __init__(self, dynamodb, index_key, start_time, end_time):
    super(QueryThread, self).__init__()
    self.dynamodb = dynamodb
    self.index_key = index_key
    self.start_time, self.end_time = start_time, end_time

  def run(self):
    self.result = [(item['toffset'] + self.get_tbase(), item['value']) for item in \
      self.dynamodb.query_datapoints(self.index_key, self.start_time, 
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

