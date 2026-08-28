"""Shut this dashboard process down once every browser tab has disconnected,
so the next click on the Desktop shortcut starts a genuinely fresh process
instead of reconnecting to one still running yesterday's code.

Why this exists: launch_dashboard.ps1 (see tools/) checks whether something is
already listening on port 8501 and, if so, just reopens the browser to it
instead of starting a new instance -- correct behavior if the dashboard is
still open in another tab, but a footgun if the old process never exited,
since closing a browser window doesn't stop a server process on its own. A
real incident: a Streamlit process launched hours earlier (before a same-day
`storage/` -> `data/` rename) kept running, and the next shortcut click just
reopened a browser to that stale process, which then threw
FileNotFoundError on the deleted path. This watcher makes "close every
browser tab" and "the server is free to shut down" the same event, so the
port reliably frees up and the reuse-check in launch_dashboard.ps1 does the
right thing.

Streamlit re-executes app.py's top level on every rerun (widget click, etc.),
but this module itself stays cached in sys.modules for the life of the
process -- so a module-level flag is what makes init() safe to call from
app.py on every rerun while only ever starting one watcher thread.
"""

import os
import threading
import time

_watcher_started = False


class IdleShutdownWatcher:
    """Pure state machine for the shutdown decision -- kept separate from the
    thread/sleep loop so the logic (grace period, "wait for the first
    connection before arming") can be unit-tested with a fake clock instead
    of real sleeps.
    """

    def __init__(self, idle_grace_seconds=10):
        self.idle_grace_seconds = idle_grace_seconds
        self._ever_connected = False
        self._idle_since = None

    def tick(self, active_sessions, now):
        """Feed in the current active-session count and a monotonic
        timestamp; returns True exactly once the process should shut down.
        """
        if active_sessions > 0:
            self._ever_connected = True
            self._idle_since = None
            return False
        if not self._ever_connected:
            # Still waiting for the first browser tab to connect after
            # launch -- 0 sessions here is the normal startup state, not
            # "everyone left".
            return False
        if self._idle_since is None:
            self._idle_since = now
            return False
        return (now - self._idle_since) >= self.idle_grace_seconds


def init(idle_grace_seconds=10, poll_interval_seconds=2):
    """Start the watcher thread, once per process. Call from app.py."""
    global _watcher_started
    if _watcher_started:
        return
    _watcher_started = True

    def _run():
        # Imported lazily so this module has no import-time dependency on a
        # Runtime instance existing yet.
        from streamlit.runtime.runtime import Runtime

        watcher = IdleShutdownWatcher(idle_grace_seconds=idle_grace_seconds)
        while True:
            time.sleep(poll_interval_seconds)
            if not Runtime.exists():
                continue
            active = Runtime.instance().num_active_sessions()
            if watcher.tick(active, time.monotonic()):
                # Hard exit, not sys.exit() -- this is a background daemon
                # thread with no cleanup to run, and os._exit guarantees the
                # port is released immediately rather than waiting on
                # Tornado/asyncio's graceful-shutdown machinery.
                os._exit(0)

    threading.Thread(target=_run, daemon=True).start()
