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

from decimal import Decimal, Context, Clamped, Overflow, Inexact, Rounded, Underflow
from threading import Thread
import random, math
from tests.data import *

AMONDAWA_CONTEXT = Context(Emin=-128, Emax=126, prec=38)

class TestPattern(object):
  """Generate random frequency data patterns based on sin(t).
  """
  def drange(start, stop, step):
    r = start
    while r <= stop:
      yield r
      r += step

  period = [d for d in drange(.1, 2, .05)]

  def __init__(self, min_value, max_value):
    self.type = random.choice([lambda v: int(v), lambda v: str(round(float(v), 3))])
    self.n = 0
    self.f = random.choice(TestPattern.period)
    self.min_value = min_value
    self.max_value = max_value

  def value(self, t):
    value = self.type((self.max_value - self.min_value) * \
        (math.sin(self.f*self.n*math.pi/180.) + 1) /2 + self.min_value)
    self.n += 1
    return AMONDAWA_CONTEXT.create_decimal(value)

  def _value(self, t):
    return Decimal ('534352.989')

  #  test non-numeric data TODO: move this to a separate location
  def _value(self, t):
    return ['ab', 'cd', 'ef']

  def _value(self, t):
    return {'ab': 'cd', 'ef' :1 }

  def _value(self, t):
    return {'queries': [{'results': [{'name': 'bytes_out',
      'tags': {'color': 'Oranges_1.0',
        'group': 'group4',
        'host': '172.4.5.1',
        'match': 'aaaaaaaa',
        'name': 'werner',
        'protected': 'protected',
        'type': 'storage'},
      'values': [[1388527883458, {'ab': 'cd', 'ef': 1}],
        [1388527885119, {'ab': 'cd', 'ef': 1}],
        [1388527886120, {'ab': 'cd', 'ef': 1}],
        [1388527887120, {'ab': 'cd', 'ef': 1}],
        [1388527888121, {'ab': 'cd', 'ef': 1}],
        [1388527889122, {'ab': 'cd', 'ef': 1}],
        [1388527890129, {'ab': 'cd', 'ef': 1}],
        [1388527891129, {'ab': 'cd', 'ef': 1}],
        [1388527892130, {'ab': 'cd', 'ef': 1}],
        [1388527893131, {'ab': 'cd', 'ef': 1}],
        [1388527894131, {'ab': 'cd', 'ef': 1}]]}],
      'sample_size': 11}]}


class MetricWriter(Thread):
  """Generate metrics, tags, datapoints.
  """
  def __init__(self, domain, metric, tags, min_value, max_value, sleeptime, 
      batch_size=20, duration=10):
    super(MetricWriter, self).__init__()
    self.datagen = TestPattern(min_value, max_value)
    self.metric = metric
    self.tags = tags
    self.min_value = min_value
    self.max_value = max_value
    self.sleeptime = sleeptime
    self.duration = duration
    self.batch_size = batch_size
    self.count = 0
    self.paused = False
    self.stopped = False

    self.daemon = True

  def reset_stats(self):
    self.count = 0

  def pause(self):
    self.paused = True

  def unpause(self):
    self.paused = False

  def stop(self):
    self.stopped = True

  def metric_desc(self):
    return all_metrics[self.metric]

  def __str__(self):
    return str((self.metric, self.tags))

class RandomWriter(MetricWriter):
  """Generate random metrics, tags, datapoints.
  """
  def __init__(self, rate=1, batch_size=20, duration=10):
    metric = random.choice(all_metrics.keys())
    min_value, max_value = all_metrics[metric]['range']
    tags = dict(map(lambda kv: [kv[0], random.choice(kv[1])], 
      all_tags.items()))
    domain = random.choice(all_domains)
    super(RandomWriter, self).__init__(domain, metric, tags, min_value, 
        max_value, 1/Decimal(rate), batch_size=batch_size, duration=duration)



