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

from pprint import pprint
from tests.writers import RandomWriter
import httplib
import simplejson, time

THREAD_RATE = 2    # per/sec

class RandomHTTPWriter(RandomWriter):
  """Write random metrics, tags, datapoints to amondawa datastore via HTTP.
  """
  def __init__(self, host, port, path, rate=THREAD_RATE):
    super(RandomHTTPWriter, self).__init__(rate) 
    self.connection = httplib.HTTPConnection(host, port)
    self.path = path
    self.dps = [{
      'name': self.metric,
      'tags': self.tags,
    }]

  def reset(self):
    datapoints = self.dps[0]['datapoints'] = []
    return datapoints

  def run(self):
    stop_time = time.time() + 60*self.total_time 
    count = 0
    datapoints = self.reset()
    while time.time() < stop_time:
      time.sleep(self.sleeptime)
      t = int(round(time.time() * 1000))
      datapoints.append([t, self.datagen.value(t)])
      count += 1
      if not count % self.set_size:
        self.send()
        datapoints = self.reset()

    if len(datapoints):
      self.send()

    self.connection.close()

  def send(self):
    self.connection.request("POST", self.path, simplejson.dumps(self.dps),
      {'Content-Type': 'application/json'})
    response = self.connection.getresponse()
    data = response.read()


