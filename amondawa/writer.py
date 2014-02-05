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


from amondawa import config
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, Thread
import sched, time, traceback

config = config.get()


class ScheduledIOPool(Thread):
    """Schedule events to an IO worker pool.
    """

    def __init__(self, workers, delay):
        super(ScheduledIOPool, self).__init__()
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.thread_pool = ThreadPoolExecutor(max_workers=workers)
        self.delay = delay
        self.shutdown = False
        self.daemon = True

    def shutdown(self):
        self.shutdown = True

    # TODO shutdown
    def run(self):
        while not self.shutdown:
            try:
                self.scheduler.run()
                time.sleep(.1)    # TODO: no wait/notify when queue is empty
            except:     # TODO log
                print "Unexpected error scheduling IO:"
                traceback.print_exc()
                time.sleep(.1)
        self.thread_pool.shutdown()

    def cancel(self, event):
        return self.scheduler.cancel(event)

    def schedule(self, *args):
        return self.scheduler.enter(self.delay, 1,
                                    self.thread_pool.submit, args)


class TimedBatchTable(object):
    """Schedule batch_writer flush events to an IO worker pool.  Datapoints are
     flushed when buffer is full OR DELAY timer expires.
    """

    io_pool = ScheduledIOPool(int(config.MT_WRITERS), int(config.MT_WRITE_DELAY))
    io_pool.start()

    #TODO where is this called?
    @staticmethod
    def shutdown():
        TimedBatchTable.io_pool.shutdown()

    def __init__(self, batch_table):
        self.lock = Lock()  # lock for datastores dict
        self.batch_table = batch_table
        self.flush_event = None

    def flush(self):
        self.batch_table.flush()

    def put_item(self, *args, **kwargs):
        with self.lock:
            if self.flush_event:
                try:
                    TimedBatchTable.io_pool.cancel(self.flush_event)
                except ValueError:  # TODO log
                    print "warning: flush_event event expired."
            self.batch_table.put_item(*args, **kwargs)
            self.flush_event = TimedBatchTable.io_pool.schedule(self._flush)

    def _flush(self):
        try:
            with self.lock:
                self.flush_event = None
                self.batch_table.flush()
        except:       # TODO log
            print "Unexpected error flushing datapoints:"
            traceback.print_exc()
