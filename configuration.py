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

MIN=60*1000
HR=60*MIN

configuration = {
 'store_column_height':   5*MIN,        # milliseconds of measurements in a datapoints hashkey
 'store_history':         1*HR,         # milliseconds of history to store (more will be deleted)
 'store_history_blocks':  3,            # history will be divided into this many archive blocks
 'mt_readers':            20,           # number of datapoints query threads
 'mt_writers':            5,            # number of datapoints writer threads
 'mt_write_delay':        2,            # number of seconds to wait for more datapoints before flushing 
                                        #   datapoints write buffer
 'cache_datapoints':      400,          # datapoints LRU cache size
 'cache_query_index_key': 400,          # index_key (query) LRU cache size
 'cache_write_index_key': 400,          # index_key (write) LRU cache size
 'tp_write_datapoints':   160,          # dynamo datapoints table write throughput
 'tp_read_datapoints':    80,           # dynamo datapoints table read throughput
 'tp_write_index_key':    160,          # dynamo index key table write throughput
 'tp_read_index_key':     80,           # dynamo index key table read throughput
 'mx_create_next_min':    4,            # cutoff time in minutes remaining for creating next datapoints tables
 'mx_create_next_pct':    15,           # cutoff time in percent remaining for creating next datapoints tables
 'mx_turndown_min':       2,            # cutoff time in minutes expired for turning down write throughput
 'mx_turndown_pct':       20,           # cutoff time in percent expired for turning down write throughput
}
