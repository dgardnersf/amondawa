# Copyright 2010 Google Inc.
# Copyright (c) 2011 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2011, Eucalyptus Systems, Inc.
# Copyright (c) 2013 Daniel Gardner
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
HTTP authentication related classes.
"""

from boto.pyami.config import Config
from boto.auth import HmacAuthV4Handler
from boto.provider import Provider
from datetime import datetime

MAX_SKEW = 15*60    # 15 minutes

class AmzAuthBuilder(object):
  def __init__(self, config, host=None):
    self.hmac = HmacAuthV4Handler(host, config, Provider('aws'))
    self.protocol = 'http'

  def _reset(self, host, port, method, path, body, headers):
    self.host = host
    self.port = port
    self.method = method
    self.auth_path = self.path = path
    self.params = {}
    self.body = body
    self.headers = headers

  def add_auth(self, host, port, method, path, body, headers):
    self._reset(host, port, method, path, body, headers)
    self.hmac.host = host
    self.hmac.add_auth(self)
    return self.headers

  def check_auth(self, host, port, method, path, body, headers):
    """Modified version of boto HmacAuthV4Handler.add_auth. The original class
        always adds an X-Amz-Date header and we don't want to do that to validate
        the credentials.
    """
    self._reset(host, port, method, path, body, headers)
    self.hmac.host = host
    qs = self.hmac.query_string(self)
    if qs and self.method == 'POST':
        # Stash request parameters into post body
        # before we generate the signature.
        self.body = qs
        self.headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        self.headers['Content-Length'] = str(len(self.body))
    else:
        # Safe to modify req.path here since
        # the signature will use req.auth_path.
        self.path = self.path.split('?')[0]
        self.path = self.path + '?' + qs
    canonical_request = self.hmac.canonical_request(self)
    string_to_sign = self.hmac.string_to_sign(self, canonical_request)
    signature = self.hmac.signature(self, string_to_sign)
    headers_to_sign = self.hmac.headers_to_sign(self)
    l = ['AWS4-HMAC-SHA256 Credential=%s' % self.hmac.scope(self)]
    l.append('SignedHeaders=%s' % self.hmac.signed_headers(headers_to_sign))
    l.append('Signature=%s' % signature)
    self.headers['Authorization'] = ','.join(l)

    return self.headers


def authorized(auth_builder, request):
  """Compute AWS4-HMAC-SHA256 authentication signature and return True if
     signature matches.  Return False if signature does not match or request 
     has missing or stale header information.
  """
  # TODO: really need logging here

  # sample Authorization header:
  #  AWS4-HMAC-SHA256
  #  Credential=AKIAJ4GY52GXHIRYQOVA/20131223/localhost/localhost/aws4_request,\
  #   SignedHeaders=host;x-amz-date,\
  #   Signature=358cc65b7d79afc369648fa40ec76dba4e19634e85a7c94aa27c08c9b00bb7fa

  # werkzeug Headers class - keys are case insensitive
  auth_header, host_header, date_header = \
      map(request.headers.get, ('authorization', 'host', 'x-amz-date'))

  # missing Authorization, Host or Date header
  if None in (auth_header, host_header, date_header):
    return False

  # don't messages with older than MAX_SKEW date header
  dt = datetime.utcnow() - datetime.strptime(date_header, '%Y%m%dT%H%M%SZ')
  if abs(dt.total_seconds()) > MAX_SKEW:
    return False

  headers = {}
  for k in request.headers.keys(lower=True):
    #   Authorization header must be recomputed
    if not k in ('authorization'):
      headers[k] = request.headers[k]

  # This is a hack (uppercase date header name) to reuse the boto client for
  # signature validation.  That class uses uppercase date header name.
  headers['X-Amz-Date'] = headers['x-amz-date']
  del headers['x-amz-date']

  host_port = host_header.split(':')
  if len(host_port) == 1:
    host, port = host_port[0], 80
  elif len(host_port) == 2:
    host, port = host_port
  else:
    return False
  
  # TODO: lookup secret using access_key (support > one access key)
  # compute Authorization header    
  headers = auth_builder.check_auth(host, port, 
          request.method, request.path, '', headers)

  # TODO: just compare signature (not whole header)
  return auth_header == headers['Authorization']


