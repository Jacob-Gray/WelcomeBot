"""
Copied from the excepthook.py (https://github.com/Charcoal-SE/SmokeDetector/blob/master/excepthook.py)
on Smoke Detector made by Charcoal (https://github.com/Charcoal-SE/SmokeDetector)
"""
from datetime import datetime
import os
import traceback
import threading
import sys
from datetime import datetime
from websocket import WebSocketConnectionClosedException
import requests


def uncaught_exception(exctype, value, tb):
    now = datetime.utcnow()
    delta = now - datetime.utcnow()
    seconds = delta.total_seconds()
    tr = '\n'.join((traceback.format_tb(tb)))
    exception_only = ''.join(traceback.format_exception_only(exctype, value)).strip()
    logged_msg = exception_only + '\n' + str(now) + " UTC" + '\n' + tr + '\n\n'
    print(logged_msg)
    with open("errorLogs.txt", "a") as f:
        f.write(logged_msg)
    if seconds < 180 and exctype != WebSocketConnectionClosedException\
            and exctype != KeyboardInterrupt and exctype != SystemExit and exctype != requests.ConnectionError:
        os._exit(4)
    else:
        os._exit(1)


def install_thread_excepthook():
    """
    Workaround for sys.excepthook thread bug
    From
    http://spyced.blogspot.com/2007/06/workaround-for-sysexcepthook-bug.html
    (https://sourceforge.net/tracker/?func=detail&atid=105470&aid=1230540&group_id=5470).
    Call once from __main__ before creating any threads.
    If using psyco, call psyco.cannotcompile(threading.Thread.run)
    since this replaces a new-style class method.
    """
    init_old = threading.Thread.__init__

    def init(self, *args, **kwargs):
        init_old(self, *args, **kwargs)
        run_old = self.run

        def run_with_except_hook(*args, **kw):
            try:
                run_old(*args, **kw)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                sys.excepthook(*sys.exc_info())
        self.run = run_with_except_hook
    threading.Thread.__init__ = init
