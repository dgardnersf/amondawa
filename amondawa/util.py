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
Utility classes - string manipulation, key <-> string conversion etc.
"""

import hashlib, time
from repoze.lru import lru_cache

#COLUMN_HEIGHT = 3*7*24*60*60*1000  # 3 weeks (in millis)
# TODO: make configurable COLUMN_HEIGHT
COLUMN_HEIGHT = 1*60*1000   # 1 minutes

def base_time(timestamp):
  """Given absolute time in epoch milliseconds, calculate base time for
     configured COLUMN_HEIGHT.
  """
  return timestamp - timestamp % COLUMN_HEIGHT

def offset_time(timestamp):
  """Given absolute time in epoch milliseconds, calculate offset time for
     configured COLUMN_HEIGHT.
  """
  return timestamp % COLUMN_HEIGHT

def to_millis(dt_string):
  """Convert ASCII timestamp to epoch milliseconds.
  """
  return int(1000*time.mktime(time.strptime(dt_string)))

def index_hash_key(domain, metric):
  """Create index hash key.
  """
  return '|'.join([domain, metric])

def index_range_key(timestamp, tags):
  """Create index range key.
  """
  return '|'.join(map(str, [base_time(timestamp), tag_string(tags)]))

def data_points_key(domain, metric, timestamp, tags):
  """Create datapoints hash key data.
  """
  return '|'.join([index_hash_key(domain, metric), index_range_key(timestamp,
    tags)])

def hdata_points_key(domain, metric, timestamp, tags):
  """Create datapoints hash key.
  """
  return hdata_points_key_str(data_points_key(domain, metric, timestamp, tags))

#@lru_cache(500)
def hdata_points_key_str(key_str):
  return hashlib.sha1(key_str).hexdigest()

def tag_string(tags):
  """Create tag string from dict.
  """
  return ';'.join(map (lambda item: '='.join(item), sorted(tags.items())))

def tags_from_string(tag_string):
  """Create dict string from tag string.
  """
  return dict(map(lambda kv: kv.split('='), tag_string.split(';')))

def offset_range(index_key, start_time, end_time):
  """Given absolute start and end time of query, calculate the start and
     end index for a given bucket (index key).
  """
  start, end = 0, COLUMN_HEIGHT
  tbase = index_key.get_tbase()
  if tbase == base_time(start_time): start = offset_time(start_time)
  if tbase == base_time(end_time): end = offset_time(end_time)
  return start, end

def to_multi_map(dicts):
  """convert dicts [{k0:v0}, {k0:v1, k1:v2}] to multi_dict
     {k0: set({v0, v1}), k1: set({v2})}
  """
  # get unique tag names
  keys = set()
  map(keys.update, dicts)
  # create a results dictionary
  ret = dict([[k, set()] for k in keys])
  map(lambda d: map(lambda k: ret[k].add(d[k]), d.keys()), dicts)
  for k in ret: ret[k] = [v for v in ret[k]]
  return ret

class IndexKey(object):
  """Wrapper class for parsing and converting index key components.
  """
  def __init__(self, key):
    self.key = key
    self.tbase = self.domain = self.tag_string = self.metric = None
    self.tags = None

  def get_tags(self):
    """Parses the tags component of index key into a dict.
    """
    if not self.tags:
      self.tags = tags_from_string(self.get_tag_string())
    return self.tags

  def get_tag_string(self):
    """Returns the tags component of index key.
    """
    self.__init()
    return self.tag_string

  def get_tbase(self):
    """Returns the base time component of index key as int.
    """
    self.__init()
    return self.tbase

  def get_domain(self):
    """Returns the domain component of index key.
    """
    self.__init()
    return self.domain

  def get_metric(self):
    """Returns the metric component of index key.
    """
    self.__init()
    return self.metric

  def __init(self):
    """Lazy initialization (parsing) of index key.
    """
    if self.tbase == None:
      self.tbase, self.tag_string = self.key['tbase_tags'].split('|')
      self.tbase = int(self.tbase)
      self.domain, self.metric = self.key['domain_metric'].split('|')

  def has_tags(self, tags):
    """return True if the offered dict's kv pairs are present in this key's tags.
    """
    key_tags = self.get_tags()
    return len ([k for k in tags if k in key_tags and key_tags[k] in tags[k]]) == len(tags)

  def to_data_points_key(self):
    """return the datapoints hash key representation of this index key.
    """
    self.__init()
    return hdata_points_key(self.domain, self.metric, self.tbase,
        self.get_tags())

