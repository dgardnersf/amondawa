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
HTTP related classes.
"""

from amondawa import config
from amondawa.auth import authorized
from amondawa.datastore import QueryMetric, DataPointSet, Datastore
from amondawa.mtime import timeit

from boto.pyami.config import Config
from flask import Flask, request, json

import amondawa

app = Flask('amondawa')

datastore = Datastore(amondawa.connect(config.REGION))

@app.route('/api/v1/<domain>/datapoints', methods=['POST'])
def add_datapoints(domain):
  """Records metric data points.
  """
  if not authorized(request): return ('Forbidden', 403, [])

  for dps in DataPointSet.from_json_object(request.get_json()):
    datastore.put_data_points(dps, domain)
  return ('', 204, [])

@app.route('/api/v1/<domain>/datapoints/query', methods=['POST'])
@timeit
def query_database(domain):
  """Returns a list of metric values based on a set of criteria. Also returns a
      set of all tag names and values that are found across the data points.
  """
  if not authorized(request): return ('Forbidden', 403, [])

  # spawn all threads
  gather_threads = [datastore.query_database(query, QueryMetric.create_callback(query), domain) \
        for query in QueryMetric.from_json_object(request.get_json()) ]

  return (json.dumps( { 'queries': [{
    'sample_size': result.sample_size,
    'results': result.results
    } for result in [t.get_result() for t in gather_threads] ] } ), 200, [])

@app.route('/api/v1/<domain>/datapoints/query/tags', methods=['POST'])
def query_metric_tags(domain):
  """Same as the query but it leaves off the data and just returns the tag
      information.
  """
  if not authorized(request): return ('Forbidden', 403, [])

  return (json.dumps( { 'results': [{
    'name': query.name,
    'tags': datastore.query_metric_tags(query, domain)
    } for query in  QueryMetric.from_json_object(request.get_json())] } ), 200, [])

@app.route('/api/v1/<domain>/metricnames')
def get_metric_names(domain):
  """Returns a list of all metric names.
  """
  if not authorized(request): return ('Forbidden', 403, [])

  return (json.dumps( { 'results': 
    [name for name in datastore.get_metric_names(domain)] }), 200, [])

@app.route('/api/v1/<domain>/tagnames')
def get_tag_names(domain):
  """Returns a list of all tag names.
  """
  if not authorized(request): return ('Forbidden', 403, [])

  return (json.dumps( { 'results': 
    [name for name in datastore.get_tag_names(domain)] }), 200, [])

@app.route('/api/v1/<domain>/tagvalues')
def get_tag_values(domain):
  """Returns a list of all tag values.
  """
  if not authorized(request): return ('Forbidden', 403, [])

  return (json.dumps( { 'results': 
    [name for name in datastore.get_tag_values(domain)] }), 200, [])

#TODO
@app.route('/api/v1/<domain>/datapoints/delete', methods=['POST'])
def delete_datapoints(domain): pass

#TODO
@app.route('/api/v1/<domain>/metric/<metric_name>', methods=['DELETE'])
def delete_metric(domain, metric_name): pass

#TODO
@app.route('/api/v1/version')
def get_version(): pass

