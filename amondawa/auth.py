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
HTTP authentication related.

Sample auth header:

  AWS4-HMAC-SHA256 
      Credential=XXXXXXXXXXXXXXXXXXXX/20140107/us-west-2/amondawa/aws4_request,
      SignedHeaders=host;x-amz-date,
      Signature=d492be57cc721e09eee2f4fdb6a998e8473a485a3fe770bc41d9793c7c99c277
"""

from amondawa import config
from hashlib import sha256 as sha256

import boto
import datetime
import hmac
import posixpath
import urllib


def check_access(domain, op, permissions):
    """return True if the permissions allow access to the provided domain and
       operation
    """
    for p in permissions:
        d, o = p.split(':')
        if (d == '*' or d == domain) and o == op:
            return True
    return False


class ProxyHTTPRequest(object):
    """A class to make the rest of this code think it's operating on a 'real' request
    """

    def __init__(self, method, host, port, auth_path, headers, body='', params={}, protocol='http'):
        self.protocol = protocol
        self.host = host
        self.port = port
        self.method = method
        self.auth_path = self.path = auth_path
        self.params = params
        self.body = body
        self.headers = headers


def auth_add_auth1(aws_access_key_id, aws_secret_access_key,
                   method, host, port, path, headers, protocol='http'):
    """Client side: add auth header to headers (used by test client).
    """
    auth_add_auth(ProxyHTTPRequest(method, host, port, path, headers, protocol=protocol),
                  aws_access_key_id, aws_secret_access_key)
    return headers


######  modified boto code follows:

def auth_sign(key, msg, hex=False):
    if hex:
        sig = hmac.new(key, msg.encode('utf-8'), sha256).hexdigest()
    else:
        sig = hmac.new(key, msg.encode('utf-8'), sha256).digest()
    return sig


def auth_headers_to_sign(http_request, host):
    """Select the headers from the request that need to be included
    in the StringToSign.
    """
    host_header_value = auth_host_header(host, http_request)
    headers_to_sign = {}
    headers_to_sign = {'Host': host_header_value}
    for name, value in http_request.headers.items():
        lname = name.lower()
        if lname.startswith('x-amz'):
            headers_to_sign[name] = value
    return headers_to_sign


def auth_host_header(host, http_request):
    port = http_request.port
    secure = http_request.protocol == 'https'
    if ((port == 80 and not secure) or (port == 443 and secure)):
        return host
    return '%s:%s' % (host, port)


def auth_query_string(http_request):
    parameter_names = sorted(http_request.params.keys())
    pairs = []
    for pname in parameter_names:
        pval = str(http_request.params[pname]).encode('utf-8')
        pairs.append(urllib.quote(pname, safe='') + '=' +
                     urllib.quote(pval, safe='-_~'))
    return '&'.join(pairs)


def auth_canonical_query_string(http_request):
    # POST requests pass parameters in through the
    # http_request.body field.
    if http_request.method == 'POST':
        return ""
    l = []
    for param in sorted(http_request.params):
        value = str(http_request.params[param])
        l.append('%s=%s' % (urllib.quote(param, safe='-_.~'),
                            urllib.quote(value, safe='-_.~')))
    return '&'.join(l)


def auth_canonical_headers(headers_to_sign):
    """
    Return the headers that need to be included in the StringToSign
    in their canonical form by converting all header keys to lower
    case, sorting them in alphabetical order and then joining
    them into a string, separated by newlines.
    """
    l = sorted(['%s:%s' % (n.lower().strip(),
                           ' '.join(headers_to_sign[n].strip().split()))
                for n in headers_to_sign])
    return '\n'.join(l)


def auth_signed_headers(headers_to_sign):
    l = ['%s' % n.lower().strip() for n in headers_to_sign]
    l = sorted(l)
    return ';'.join(l)


def auth_canonical_uri(http_request):
    path = http_request.auth_path
    # Normalize the path
    # in windows normpath('/') will be '\\' so we chane it back to '/'
    normalized = posixpath.normpath(path).replace('\\', '/')
    # Then urlencode whatever's left.
    encoded = urllib.quote(normalized)
    if len(path) > 1 and path.endswith('/'):
        encoded += '/'
    return encoded


def auth_payload(http_request):
    body = http_request.body
    # If the body is a file like object, we can use
    # boto.utils.compute_hash, which will avoid reading
    # the entire body into memory.
    if hasattr(body, 'seek') and hasattr(body, 'read'):
        return boto.utils.compute_hash(body, hash_algorithm=sha256)[0]
    return sha256(http_request.body).hexdigest()


def auth_canonical_request(http_request, host):
    cr = [http_request.method.upper()]
    cr.append(auth_canonical_uri(http_request))
    cr.append(auth_canonical_query_string(http_request))
    headers_to_sign = auth_headers_to_sign(http_request, host)
    cr.append(auth_canonical_headers(headers_to_sign) + '\n')
    cr.append(auth_signed_headers(headers_to_sign))
    cr.append(auth_payload(http_request))
    return '\n'.join(cr)


def auth_scope(http_request, access_key):
    scope = [access_key]
    scope.append(http_request.timestamp)
    scope.append(http_request.region_name)
    scope.append(http_request.service_name)
    scope.append('aws4_request')
    return '/'.join(scope)


def auth_credential_scope(http_request, service_name, region_name):
    scope = []
    http_request.timestamp = http_request.headers['X-Amz-Date'][0:8]
    scope.append(http_request.timestamp)

    http_request.service_name = service_name
    http_request.region_name = region_name

    scope.append(http_request.region_name)
    scope.append(http_request.service_name)
    scope.append('aws4_request')
    return '/'.join(scope)


def auth_string_to_sign(http_request, canonical_request, service_name, region_name):
    """
    Return the canonical StringToSign as well as a dict
    containing the original version of all headers that
    were included in the StringToSign.
    """
    sts = ['AWS4-HMAC-SHA256']
    sts.append(http_request.headers['X-Amz-Date'])
    sts.append(auth_credential_scope(http_request, service_name, region_name))
    sts.append(sha256(canonical_request).hexdigest())
    return '\n'.join(sts)


def auth_signature(http_request, string_to_sign, secret_key):
    key = secret_key
    k_date = auth_sign(('AWS4' + key).encode('utf-8'),
                       http_request.timestamp)
    k_region = auth_sign(k_date, http_request.region_name)
    k_service = auth_sign(k_region, http_request.service_name)
    k_signing = auth_sign(k_service, 'aws4_request')
    return auth_sign(k_signing, string_to_sign, hex=True)


def auth_add_auth(req, access_key, secret_key, service_name='amondawa', region_name=config.REGION):
    """
    Add AWS4 authentication to a request.

    :type req: :class`boto.connection.HTTPRequest`
    :param req: The HTTPRequest object.
    """
    # This could be a retry.  Make sure the previous
    # authorization header is removed first.
    if 'X-Amzn-Authorization' in req.headers:
        del req.headers['X-Amzn-Authorization']
    now = datetime.datetime.utcnow()
    req.headers['X-Amz-Date'] = now.strftime('%Y%m%dT%H%M%SZ')

    auth_check_auth(req, access_key, secret_key, service_name, region_name)


def auth_check_auth(req, access_key, secret_key, service_name='amondawa', region_name=config.REGION):
    """
    Add AWS4 authentication to a request.

    :type req: :class`boto.connection.HTTPRequest`
    :param req: The HTTPRequest object.
    """
    qs = auth_query_string(req)
    if qs and req.method == 'POST':
        # Stash request parameters into post body
        # before we generate the signature.
        req.body = qs
        req.headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        req.headers['Content-Length'] = str(len(req.body))
    else:
        # Safe to modify req.path here since
        # the signature will use req.auth_path.
        req.path = req.path.split('?')[0]
        req.path = req.path + '?' + qs
    canonical_request = auth_canonical_request(req, req.host)
    # TODO: logging
    #print 'CanonicalRequest:\n%s' % canonical_request
    string_to_sign = auth_string_to_sign(req, canonical_request, service_name, region_name)
    #print 'StringToSign:\n%s' % string_to_sign
    signature = auth_signature(req, string_to_sign, secret_key)
    #print 'Signature:\n%s' % signature
    headers_to_sign = auth_headers_to_sign(req, req.host)
    l = ['AWS4-HMAC-SHA256 Credential=%s' % auth_scope(req, access_key)]
    l.append('SignedHeaders=%s' % auth_signed_headers(headers_to_sign))
    l.append('Signature=%s' % signature)
    req.headers['Authorization'] = ','.join(l)


