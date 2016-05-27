# -*- coding: utf-8 -*-
'''
    :codeauthor: :email:`Pedro Algarvio (pedro@algarvio.me)`
    :copyright: © 2016 by the SaltStack Team, see AUTHORS for more details.
    :license: Apache 2.0, see LICENSE for more details.


    pytestsalt.salt.log_handlers.pytest_log_handler
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Salt External Logging Handler
'''

# Import python libs
from __future__ import absolute_import
import socket
import threading
import logging
import msgpack
import salt.log.setup
from multiprocessing import Queue

__virtualname__ = 'pytest_log_handler'

log = logging.getLogger(__name__)

def __virtual__():
    if 'pytest_log_port' not in __opts__:
        return False, "'pytest_log_port' not in options"
    return True


def setup_handlers():
    queue = Queue()
    handler = salt.log.setup.QueueHandler(queue)
    handler.setLevel(1)
    process_queue_thread = threading.Thread(target=process_queue,
                                            args=(__opts__['pytest_log_port'],
                                                  __opts__['pytest_log_prefix'],
                                                  queue))
    process_queue_thread.daemon = True
    process_queue_thread.start()
    return handler


def process_queue(port, prefix, queue):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', port))
    while True:
        try:
            record = queue.get()
            if record is None:
                # A sentinel to stop processing the queue
                break
            # Just send every log. Filtering will happen on the main process
            # logging handlers
            record_dict = record.__dict__
            record_dict['msg'] = prefix + record_dict['msg']
            sock.sendall(msgpack.dumps(record_dict, encoding='utf-8'))
        except (IOError, EOFError, KeyboardInterrupt, SystemExit):
            break
        except Exception as exc:  # pylint: disable=broad-except
            log.warning(
                'An exception occurred in the pytest salt logging '
                'queue thread: {0}'.format(exc),
                exc_info_on_loglevel=logging.DEBUG
            )
