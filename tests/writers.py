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

from decimal import Decimal, Context
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
                          (math.sin(self.f * self.n * math.pi / 180.) + 1) / 2 + self.min_value)
        self.n += 1
        return AMONDAWA_CONTEXT.create_decimal(value)


class MetricWriter(Thread):
    """Generate metrics, tags, datapoints.
    """
    n = 0
    def __init__(self, rate=1, batch_size=20, duration=10, random_values=True):
        super(MetricWriter, self).__init__()
        if random_values:
            self._random_init()
        else:
            self._simple_init()

        self.datagen = TestPattern(self.min_value, self.max_value)
        self.sleeptime = 1 / Decimal(rate)
        self.duration = duration
        self.batch_size = batch_size
        self.count = 0
        self.paused = False
        self.stopped = False

        self.daemon = True

    def _simple_init(self):
        self.metric = sorted(all_metrics.keys())[0:1]
        self.min_value, self.max_value = all_metrics[self.metric]['range']
        self.tags = dict(map(lambda kv: [kv[0], kv[1][MetricWriter.n]],
                        sorted(all_tags.items())))
        MetricWriter.n += 1
        self.domain = all_domains[0]

    def _random_init(self):
        self.metric = random.choice(all_metrics.keys())
        self.min_value, self.max_value = all_metrics[self.metric]['range']
        self.tags = dict(map(lambda kv: [kv[0], random.choice(kv[1])],
                        all_tags.items()))
        self.domain = random.choice(all_domains)

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

