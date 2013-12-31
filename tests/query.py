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

import simplejson, httplib
from threading import Thread

from amondawa.auth import AmzAuthBuilder
from boto.pyami.config import Config

class QueryRunner(Thread):
  URI = '/api/v1/nodomain/datapoints/query'
  HEADERS = {'Content-Type': 'application/json'}

  def __init__(self, host, port):
    super(QueryRunner, self).__init__()
    self.host = host
    self.port = port
    self._connect()
    self.auth_builder = AmzAuthBuilder(Config('./client.cfg'))  # TODO: move up cfg
    
  def perform_query(self, query):
    return self._perform_query(simplejson.dumps(query))

  def _perform_query(self, query):
    try:
      headers = self.auth_builder.add_auth(self.host, self.port, 
          'POST', QueryRunner.URI, '', QueryRunner.HEADERS)
      self.connection.request("POST", QueryRunner.URI, query, headers)
      return self.connection.getresponse()
    except:
      self._connect()
      self.connection.request("POST", QueryRunner.URI, query, headers)
      return self.connection.getresponse()
 
  def _connect(self):
    self.connection = httplib.HTTPConnection(self.host, self.port)

  def run(self):
    pass
