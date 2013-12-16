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

from time import time, asctime, localtime
import random

class Intervals(object):
  """Basic stats and timings.
  """
  def __init__(self):
    self.intervals = []
    self.totals = []

  def start_interval(self):
    """Start a new interval.
    """
    assert not self.running()
    self.intervals.append([time()])

  def end_interval(self, totals):
    """Stop the current interval.
    """
    assert self.running()
    self.totals.append(Intervals._sum(totals))
    self.intervals[-1].append(time())

  def running(self):
    return self.intervals and len(self.intervals[-1]) == 1

  def paused(self):
    return not self.running()

  def print_history(self, current):
    current = Intervals._sum(current)
    if self.running():
      print '---------'
      print self.range_str(self.intervals[-1]), "(CURRENT)"
      print '---------'
      print current
      print 'rate:', self.rates(current, self.intervals[-1])

    if not self.totals: return
    i = 0
    for total in self.totals:
      print '---------'
      print self.range_str(self.intervals[i])
      print '---------'
      print total
      print 'rate:', self.rates(total, self.intervals[i])
      i += 1

    total_time = self.total_time()
    total = Intervals._sum(self.totals + [current])
    print '---------'
    print 'total'
    print '---------'
    print total
    for k in total:
      total[k] /= total_time 
    print 'rate:', total
 
  def range_str(self, interval):
    if len(interval) == 2:
      start, end = interval
    else:
      start, end = interval[0], time()
    return "%s - %s, (%s sec)" % (asctime(localtime(start)), 
                                  asctime(localtime(end)),
                                  end - start)

  def rates(self, totals, interval):
    totals = totals.copy()
    elapsed = self.elapsed(interval)
    for k in totals:
      totals[k] /=  elapsed
    return totals

  def elapsed(self, interval):
    if len(interval) == 2:
      return interval[1] - interval[0]
    else:
      return time() - interval[0]

  def current_elapsed(self):
    if self.running():
      return self.elapsed(self.intervals[-1])
    return 0

  def total_completed_time(self):
    return sum(map(self.elapsed, self._closed_intervals()))

  def total_time(self):
    return self.current_elapsed() + self.total_completed_time() 

  def choose_random_interval(self):
    start_interval = random.randrange(0, len(self.intervals))
    end_interval = random.randrange(start_interval, len(self.intervals))

    start = self._choose_random_time(self.intervals[start_interval])
    end = self._choose_random_time(self.intervals[end_interval], start)

    return start, end

  def _closed_intervals(self):
    return filter(lambda i: len(i) == 2, self.intervals)

  def _choose_random_time(self, interval, start=None):
    if start == None:
      start = int(1000*interval[0])
    if len(interval) == 1:
      end = int(1000*time())
    else:
      end = int(1000*interval[1])

    return random.randrange(start, end + 1)

  @staticmethod
  def _sum(dicts):
    ret = {}
    for t in dicts:
      if not ret:
        ret.update(t)
      else:
        for k in t: ret[k] += t[k]
    return ret

