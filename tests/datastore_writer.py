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

from amondawa.datastore import Datastore, DataPoint, DataPointSet
from tests.writers import RandomWriter
import time


class RandomDatastoreWriter(RandomWriter):
  """Write random metrics, tags, datapoints directly to amondawa datastore.
  """
  def __init__(self, connection, rate=1):
    super(RandomDatastoreWriter, self).__init__(rate) 
    self.datastore = Datastore(connection)

  def run(self):
    dps = DataPointSet(self.metric, self.tags)
    stop_time = time.time() + 60*self.total_time 
    self.count = 0
    while time.time() < stop_time:
      time.sleep(self.sleeptime)
      t = int(round(time.time() * 1000))
      value = self.datagen.value(t)
      dps.append(DataPoint(t, value))
      self.count += 1
      if not self.count % self.batch_size:
        self.datastore.put_data_points(dps)
        dps = DataPointSet(self.metric, self.tags)

    if len(dps):
      self.datastore.put_data_points(dps)
    self.datastore.close()

