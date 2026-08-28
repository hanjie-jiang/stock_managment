"""IdleShutdownWatcher's tick() is a pure state machine (see auto_shutdown.py
docstring for why) -- tested here with a fake clock, no real threads/sleeps."""

from shell.auto_shutdown import IdleShutdownWatcher


def test_does_not_shut_down_before_first_connection():
    w = IdleShutdownWatcher(idle_grace_seconds=10)
    # 0 active sessions right after launch (browser hasn't opened yet) must
    # not be mistaken for "everyone left".
    for t in range(0, 30, 2):
        assert w.tick(active_sessions=0, now=t) is False


def test_shuts_down_after_grace_period_once_idle():
    w = IdleShutdownWatcher(idle_grace_seconds=10)
    w.tick(active_sessions=1, now=0)  # browser connects
    assert w.tick(active_sessions=0, now=1) is False  # just disconnected
    assert w.tick(active_sessions=0, now=5) is False  # within grace period
    assert w.tick(active_sessions=0, now=10.9) is False  # just under the line
    assert w.tick(active_sessions=0, now=11) is True  # grace period elapsed


def test_reconnect_within_grace_period_cancels_shutdown():
    """A page refresh disconnects and reconnects within a second or two --
    must not shut down partway through a refresh."""
    w = IdleShutdownWatcher(idle_grace_seconds=10)
    w.tick(active_sessions=1, now=0)
    w.tick(active_sessions=0, now=1)  # refresh: old session drops
    assert w.tick(active_sessions=1, now=2) is False  # new session connects
    # Idle clock must have reset -- another 9s of 0 sessions shouldn't fire.
    assert w.tick(active_sessions=0, now=11) is False


def test_shuts_down_again_after_a_second_idle_period():
    w = IdleShutdownWatcher(idle_grace_seconds=10)
    w.tick(active_sessions=1, now=0)
    w.tick(active_sessions=0, now=1)
    assert w.tick(active_sessions=0, now=12) is True
    # A second browser connects later, then leaves again -- should be able
    # to fire a second time (tick() only returns True once per idle episode,
    # but a fresh idle episode after a reconnect should re-arm).
    w.tick(active_sessions=1, now=20)
    w.tick(active_sessions=0, now=21)
    assert w.tick(active_sessions=0, now=25) is False
    assert w.tick(active_sessions=0, now=32) is True
