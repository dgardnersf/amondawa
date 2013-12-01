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

from amondawa.datastore import Datastore, DataPointSet, QueryMetric, SimpleQueryCallback
from flask import Flask, request, json
from pprint import pprint
import amondawa

app = Flask('amondawa')

connection = amondawa.connect('us-west-2')
datastore = Datastore(connection)

import logging
logging.getLogger().addHandler(logging.StreamHandler())

@app.route('/api/v1/datapoints', methods=['POST'])
def add_datapoints():
  json = request.get_json()
  for dps in DataPointSet.from_json_object(json):
    datastore.put_data_points(dps)
  return ('', 204, [])

@app.route('/api/v1/datapoints/query', methods=['POST'])
def query_database():
  results = { 'queries': [{
    'sample_size': result.sample_size,
    'results': result.results
    } for result in [datastore.query_database(query, SimpleQueryCallback(query.name)) \
        for query in QueryMetric.from_json_object(request.get_json())] ] }
  return (json.dumps(results), 200, [])

@app.route('/api/v1/datapoints/query/tags', methods=['POST'])
def query_metric_tags():
  pass

@app.route('/api/v1/datapoints/delete', methods=['POST'])
def delete_datapoints():
  pass

@app.route('/api/v1/metric/<metric_name>', methods=['DELETE'])
def delete_metric(metric_name):
  pass

@app.route('/api/v1/metricnames')
def get_metric_names():
  pass

@app.route('/api/v1/tagnames')
def get_tag_names():
  pass

@app.route('/api/v1/tagvalues')
def get_tag_values():
  pass

@app.route('/api/v1/version')
def get_version():
  pass


