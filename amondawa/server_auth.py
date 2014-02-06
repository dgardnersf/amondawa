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

from amondawa.schema import Schema
from auth import check_access, auth_check_auth, ProxyHTTPRequest
import amondawa
import config
import datetime

# TODO: make configurable? maybe more secure hardcoded
MAX_SKEW = 15 * 60          # 15 minutes

schema = Schema(amondawa.connect(config.REGION))
# scan the credentials table  TODO: periodically scan
amdw_credentials = schema.get_credentials()

def authorized(request, domain, op):
    """Compute AWS4-HMAC-SHA256 authentication signature and return True if
     signature matches.  Return False if signature does not match or request
     has missing or stale header information.

     Performs HMAC authentication and domain:operation authorization.
    """
    # TODO: really, really need debug logging here
    # TODO: think more about order (e.g. permissions authz before
    #            or after authn)

    # werkzeug Headers class - keys are case insensitive
    auth_header, host_header, date_header = \
        map(request.headers.get, ('authorization', 'host', 'x-amz-date'))

    # missing Authorization, Host or Date header
    if None in (auth_header, host_header, date_header):
        return False

    # don't allow messages with older than MAX_SKEW date header
    dt = datetime.datetime.utcnow() - datetime.datetime.strptime(date_header, '%Y%m%dT%H%M%SZ')
    if abs(dt.total_seconds()) > MAX_SKEW:
        return False

    # try to parse auth header
    try:
        _, parts = auth_header.split()
        credentials, signed_headers, signature = parts.split(',')
        _, credentials = credentials.split('=')
        aws_access_key_id = credentials.split('/')[0]
        record = amdw_credentials.get(aws_access_key_id)
        if not record:
            return False
        if record.state != 'ACTIVE': return False
        aws_secret_access_key = record.secret_access_key
    except:
        # cannot find access_key_id or secret_access_key
        return False

    # check domain:operation permissions
    if not check_access(domain, op, record.permissions):
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

    #TODO: protocol (http/http(s)) must come from the request URI
    #print auth_header
    prequest = ProxyHTTPRequest(request.method, host, port,
                                request.path, headers, protocol='http')

    auth_check_auth(prequest, aws_access_key_id, aws_secret_access_key)
    # TODO: just compare signature (not whole header)
    return auth_header == headers['Authorization']



