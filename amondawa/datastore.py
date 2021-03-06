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

from amondawa import util
from amondawa.mtime import timeit
from amondawa.query import AggegatingQueryCallback, ComplexQueryCallback
from amondawa.query import QueryTask, GatherTask, FREQ_MILLIS
from amondawa.query import SimpleQueryCallback, ResamplingQueryCallback
from amondawa.schema import Schema

import time


class Datastore(object):
    """Object based access to the time series database.
    """

    def __init__(self, connection):
        """ctor
        """
        self.connection = connection
        self.dynamodb = Schema(connection, start_mx=True)

    def put_data_points(self, dps, domain):
        """Store elements of DataPointSet.
        """
        for dp in dps:
            self.dynamodb.store_datapoint(dp.timestamp, dps.name, dps.tags, dp.value,
                                          domain)

    def get_metric_names(self, domain):
        """Get the names of the metrics in the database.
        """
        return self.dynamodb.get_metric_names(domain)

    def get_tag_names(self, domain):
        """Get the names of the tags in the database.
        """
        return self.dynamodb.get_tag_names(domain)

    def get_tag_values(self, domain):
        """Get the values of the tags in the database.
        """
        return self.dynamodb.get_tag_values(domain)

    @timeit
    def query_database(self, query, query_callback, domain):
        """Query datapoints by time interval and tags.
        """
        # for each matching index key, create a datapoints query thread
        query_threads = []
        for index_key in self._query_index_keys(query.name, query.start_time,
                                                query.end_time, query.tags, domain):
            query_threads.append(QueryTask(self.dynamodb, index_key,
                                           query.start_time, query.end_time))

        # start the query threads
        for query in query_threads:
            query.start()

        gather_thread = GatherTask(query_threads, query_callback)
        gather_thread.start()

        return gather_thread

    def query_metric_tags(self, query, domain):
        """Query datapoint tags by time interval and tags.
        """
        # get index keys (domain_metric_tbase_tags)
        index_keys = self._query_index_keys(query.name,
                                            query.start_time, query.end_time, query.tags, domain)
        # convert tag part to kv pair dictionaries
        return util.to_multi_map([key.get_tags() for key in index_keys])

    def delete_data_points(self, delete_query):
        """Delete datapoints by time interval and tags.
        """
        pass

    def close(self):
        """Flush any cached state and close connections.
        """
        self.dynamodb.close()

    @timeit
    def _query_index_keys(self, metric, start_time, end_time, tags, domain):
        """Query index keys by time interval and tags.
        """
        return filter(lambda key: len(tags) == 0 or key.has_tags(tags),
                      self.dynamodb.query_index(domain, metric, start_time, end_time))


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


class DataPointSet(list):
    """A collection of datapoints.
    """

    @classmethod
    def from_json_object(cls, json):
        """Factory method: datapoints from json.
        """
        ret = []
        for o in json:
            dps = cls(o['name'], o['tags'])
            if 'timestamp' in o:
                dps.append(DataPoint(o['timestamp'], util.to_dynamo_compat_type(o['value'])))
            elif 'datapoints' in o:
                for timestamp, value in o['datapoints']:
                    dps.append(DataPoint(timestamp, util.to_dynamo_compat_type(value)))
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
        return self is o or (type(o) == DataPointSet and
                             self.data_points == o.data_points and
                             self.name == o.name and self.tags == o.tags)


class QueryMetric(object):
    """DataPoint query class.
    """

    @classmethod
    def from_json_object(cls, json):
        """Factory method: query from json.
        """
        start, end = cls._time_interval_from_json(json)
        return [cls(start, end, metric['name'], metric.get('aggregate'),
                    metric.get('downsample'), metric['tags']) for metric in json['metrics']]

    @staticmethod
    def create_callback(query):
        aggregator = resampler = None
        if query.aggregator:
            aggregator = AggegatingQueryCallback(query.name, query.aggregator)
        if query.downsample:
            resampler = ResamplingQueryCallback(query.name, query.downsample['name'],
                                                query.downsample['sampling']['value'],
                                                query.downsample['sampling']['unit'])
        if aggregator:
            if resampler:     # both are specified
                return ComplexQueryCallback(aggregator, resampler)
            else:             # only aggregator, use default (1 second) resampler
                return aggregator

        if resampler:
            return resampler  # only downsample

        # none specified
        return SimpleQueryCallback(query.name)

    @staticmethod
    def _calc_time(now, json, stend):
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
                FREQ_MILLIS[relative['unit']]
        return t

    @classmethod
    def _time_interval_from_json(cls, json):
        """Calculate absolute time from absolute timestamp or relative time struct.
        """
        now = int(round(time.time() * 1000))
        return (cls._calc_time(now, json, stend) \
                for stend in ('start', 'end'))

    def __init__(self, start_time, end_time, name, aggregator=None,
                 downsample=None, tags=None, cache_time=0):
        self.start_time = start_time
        self.end_time = end_time
        self.cache_time = cache_time
        self.name = name
        self.tags = tags
        self.aggregator = aggregator
        self.downsample = downsample

    def add_tag(self, name, value):
        self.tags[name] = value

    def add_group_by(self, group_by):
        pass

    def is_exclude_tags(self):
        pass

    def set_exclude_tags(self, exclude_tags):
        pass


