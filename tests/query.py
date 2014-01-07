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

from amondawa.auth import auth_add_auth1
import simplejson, httplib
from threading import Thread

class QueryRunner(Thread):
  PATH = '/api/v1/nodomain/datapoints/query'

  def __init__(self, host, port, access_key_id, secret_access_key):
    super(QueryRunner, self).__init__()
    self.access_key_id = access_key_id
    self.secret_access_key = secret_access_key
    self.host = host
    self.port = port
    self._connect()
    
  def perform_query(self, query):
    return self._perform_query(simplejson.dumps(query))

  def _perform_query(self, query):
    try:
      headers = auth_add_auth1(self.access_key_id, self.secret_access_key,
       'POST', self.host, self.port, QueryRunner.PATH, {'Content-Type': 'application/json'})
      self.connection.request('POST', QueryRunner.PATH, query, headers)
      return self.connection.getresponse()
    except:
      self._connect()
      self.connection.request('POST', QueryRunner.PATH, query, headers)
      return self.connection.getresponse()
 
  def _connect(self):
    self.connection = httplib.HTTPConnection(self.host, self.port)

  def run(self):
    pass
