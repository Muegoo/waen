import ctypes
import ctypes.wintypes
import os
import sys

import pytest

from waen.platform import get_platform
from waen.platform.noop import NoopPlatform

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Win32 only")


@pytest.fixture
def window(qt_app):
    """Yield a real HWND even while Qt uses its offscreen platform plugin."""
    if os.environ.get("QT_QPA_PLATFORM", "").lower() != "offscreen":
        from PyQt6.QtWidgets import QWidget

        widget = QWidget()
        widget.show()
        yield int(widget.winId())
        widget.close()
        return

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    kernel32.GetModuleHandleW.restype = ctypes.wintypes.HMODULE
    hinstance = kernel32.GetModuleHandleW(None)
    class_name = f"WaenCaptureExclusionTest{os.getpid()}"

    wndproc_type = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t,
        ctypes.wintypes.HWND,
        ctypes.wintypes.UINT,
        ctypes.wintypes.WPARAM,
        ctypes.wintypes.LPARAM,
    )

    @wndproc_type
    def window_proc(hwnd, message, wparam, lparam):
        return user32.DefWindowProcW(hwnd, message, wparam, lparam)

    class WNDCLASSW(ctypes.Structure):
        _fields_ = [
            ("style", ctypes.wintypes.UINT),
            ("lpfnWndProc", wndproc_type),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", ctypes.wintypes.HINSTANCE),
            ("hIcon", ctypes.wintypes.HICON),
            ("hCursor", ctypes.wintypes.HANDLE),
            ("hbrBackground", ctypes.wintypes.HBRUSH),
            ("lpszMenuName", ctypes.wintypes.LPCWSTR),
            ("lpszClassName", ctypes.wintypes.LPCWSTR),
        ]

    window_class = WNDCLASSW()
    window_class.lpfnWndProc = window_proc
    window_class.hInstance = hinstance
    window_class.lpszClassName = class_name

    user32.DefWindowProcW.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.wintypes.UINT,
        ctypes.wintypes.WPARAM,
        ctypes.wintypes.LPARAM,
    ]
    user32.DefWindowProcW.restype = ctypes.c_ssize_t
    user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
    user32.RegisterClassW.restype = ctypes.wintypes.ATOM
    user32.UnregisterClassW.argtypes = [
        ctypes.wintypes.LPCWSTR,
        ctypes.wintypes.HINSTANCE,
    ]
    user32.UnregisterClassW.restype = ctypes.wintypes.BOOL
    user32.ShowWindow.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
    user32.DestroyWindow.argtypes = [ctypes.wintypes.HWND]
    if not user32.RegisterClassW(ctypes.byref(window_class)):
        pytest.skip("could not register a native Win32 test window class")

    user32.CreateWindowExW.argtypes = [
        ctypes.wintypes.DWORD,
        ctypes.wintypes.LPCWSTR,
        ctypes.wintypes.LPCWSTR,
        ctypes.wintypes.DWORD,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.wintypes.HWND,
        ctypes.wintypes.HANDLE,
        ctypes.wintypes.HINSTANCE,
        ctypes.c_void_p,
    ]
    user32.CreateWindowExW.restype = ctypes.wintypes.HWND
    try:
        hwnd = user32.CreateWindowExW(
            0,
            class_name,
            "Waen capture exclusion test",
            0x00CF0000,  # WS_OVERLAPPEDWINDOW
            0,
            0,
            100,
            100,
            None,
            None,
            hinstance,
            None,
        )
    except Exception:
        user32.UnregisterClassW(class_name, hinstance)
        raise
    if not hwnd:
        user32.UnregisterClassW(class_name, hinstance)
        pytest.skip("could not create a native Win32 test window")

    user32.ShowWindow(hwnd, 0)  # SW_HIDE: the HWND remains a valid top-level window.
    try:
        yield int(hwnd)
    finally:
        user32.DestroyWindow(hwnd)
        user32.UnregisterClassW(class_name, hinstance)


def test_noop_platform_reports_failure_honestly():
    platform = NoopPlatform()
    assert platform.exclude_from_capture(1) is False
    assert platform.apply_overlay_styles(1) is False


def test_exclude_from_capture_succeeds_on_a_real_window(window):
    result = get_platform().exclude_from_capture(window)
    assert result is True, (
        "SetWindowDisplayAffinity failed; Windows 10 build 19041 or later is required. "
        "Older systems use the mask fallback instead."
    )


def test_exclude_from_capture_with_an_invalid_handle_returns_false():
    assert get_platform().exclude_from_capture(0) is False


def test_apply_overlay_styles_succeeds_on_a_real_window(window):
    assert get_platform().apply_overlay_styles(window) is True


def test_apply_overlay_styles_with_an_invalid_handle_returns_false():
    assert get_platform().apply_overlay_styles(0) is False
