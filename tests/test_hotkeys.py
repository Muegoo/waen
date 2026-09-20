import ctypes
import ctypes.wintypes
import sys

import pytest


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Win32 only")


def test_registering_an_unused_combo_succeeds(qt_app):
    from waen.platform.win32 import Win32Platform

    platform = Win32Platform()
    fired = []
    ok = platform.register_global_hotkeys(
        qt_app, {"toggle": "ctrl+alt+f9"}, fired.append
    )
    try:
        assert ok is True
    finally:
        platform.unregister_global_hotkeys()


def test_registering_the_same_combo_twice_fails_the_second_time(qt_app):
    from waen.platform.win32 import Win32Platform

    first = Win32Platform()
    second = Win32Platform()
    assert first.register_global_hotkeys(qt_app, {"a": "ctrl+alt+f10"}, lambda _: None)
    try:
        assert second.register_global_hotkeys(
            qt_app, {"a": "ctrl+alt+f10"}, lambda _: None
        ) is False
    finally:
        first.unregister_global_hotkeys()
        second.unregister_global_hotkeys()


def test_an_unparseable_combo_is_skipped_without_crashing(qt_app):
    from waen.platform.win32 import Win32Platform

    platform = Win32Platform()
    try:
        assert platform.register_global_hotkeys(
            qt_app, {"broken": "ctrl+alt"}, lambda _: None
        ) is False
    finally:
        platform.unregister_global_hotkeys()


def test_one_bad_combo_does_not_stop_the_good_ones(qt_app):
    from waen.platform.win32 import Win32Platform

    platform = Win32Platform()
    try:
        assert platform.register_global_hotkeys(
            qt_app, {"broken": "ctrl+alt", "good": "ctrl+alt+f11"}, lambda _: None
        ) is True
    finally:
        platform.unregister_global_hotkeys()


def test_unregister_is_safe_to_call_without_registering(qt_app):
    from waen.platform.win32 import Win32Platform

    Win32Platform().unregister_global_hotkeys()


def test_hotkey_filter_dispatches_a_simulated_wm_hotkey(qt_app):
    from waen.platform.win32 import WM_HOTKEY, Win32Platform

    platform = Win32Platform()
    fired = []
    assert platform.register_global_hotkeys(
        qt_app, {"toggle": "ctrl+alt+f12"}, fired.append
    )
    message = ctypes.wintypes.MSG()
    message.message = WM_HOTKEY
    message.wParam = platform._registered_ids[0]
    try:
        handled, result = platform._hotkey_filter.nativeEventFilter(
            b"windows_generic_MSG", ctypes.addressof(message)
        )
        assert (handled, result) == (False, 0)
        assert fired == ["toggle"]
    finally:
        platform.unregister_global_hotkeys()
