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

from tests.writers import RandomWriter
import simplejson, sys, time, httplib, pprint

from amondawa.auth import AmzAuthBuilder
from boto.pyami.config import Config

class RandomHTTPWriter(RandomWriter):
  """Write random metrics, tags, datapoints to amondawa datastore via HTTP.
  """
  def __init__(self, host, port, path='/api/v1/nodomain/datapoints', rate=20, batch_size=20, duration=10):
    super(RandomHTTPWriter, self).__init__(rate=rate, batch_size=batch_size, duration=duration) 

    self.auth_builder = AmzAuthBuilder(Config('./client.cfg'))  # TODO: move up cfg

    self.connection = httplib.HTTPConnection(host, port)
    self.port = port
    self.host = host
    self.path = path
    self.dps = [{
      'name': self.metric,
      'tags': self.tags,
    }]
    self._init_stats()

  def reset(self):
    datapoints = self.dps[0]['datapoints'] = []
    return datapoints

  def run(self):
    stop_time = time.time() + 60*self.duration 
    self.count = 0
    datapoints = self.reset()
    while time.time() < stop_time and not self.stopped:
      if self.paused:
        time.sleep(.1)
        continue
      time.sleep(self.sleeptime)
      t = int(round(time.time() * 1000))
      datapoints.append([t, self.datagen.value(t)])
      self.count += 1
      if not self.count % self.batch_size:
        self.send()
        datapoints = self.reset()

    if len(datapoints):
      self.send()

    self.connection.close()

  def status(self):
    return 'count:', self.count, \
        'http status counts: ', pprint.pformat(self.status_codes), \
        'last_exc_info:', pprint.pformat(self.last_exc_info), \
        'exceptions counts:', pprint.pformat(self.exceptions)

  def reset_stats(self):
    totals = self.totals()
    super(RandomHTTPWriter, self).reset_stats()
    self._init_stats()
    return totals

  def _init_stats(self):
    self.status_codes = {}
    self.exceptions = {}
    self.last_exc_info = ()
    self.requests = 0

  def totals(self):
    return {
        'request'     : self.requests,
        'data_points' : self.count,
        'success'     : self._total_success(),
        'failed'      : self._total_failed(),
        'error'       : sum(self.exceptions.values())
    }

  def send(self):
    try:
      headers = self.auth_builder.add_auth(self.host, self.port, 
          'POST', self.path, '', {'Content-Type': 'application/json'})
      self.connection.request('POST', self.path, simplejson.dumps(self.dps), headers)
      response = self.connection.getresponse()
      data = response.read()
      self._count_response(response)
      self.requests += 1
    except:
      self._count_error(sys.exc_info())

  def _count_error(self, exc_info):
    self.last_exc_info = type_, value, self.last_traceback = exc_info
    if type_ in self.exceptions:
      self.exceptions[type_] +=1
    else:
      self.exceptions[type_] = 1

  def _count_response(self, response):
    status = response.status
    if status in self.status_codes:
      self.status_codes[status] +=1
    else:
      self.status_codes[status] = 1

  def _total_failed(self):
    return sum([item[1] for item in filter(lambda (k, v): k >= 300,
      self.status_codes.items())])

  def _total_success(self):
    return sum([item[1] for item in filter(lambda (k, v): k < 300,
      self.status_codes.items())])


