import sys

import pytest

from waen.platform import get_platform
from waen.platform.base import PlatformIntegration
from waen.platform.noop import NoopPlatform


def test_get_platform_satisfies_the_protocol():
    assert isinstance(get_platform(), PlatformIntegration)


def test_noop_platform_is_safe_to_call_everywhere():
    platform = NoopPlatform()
    platform.make_dpi_aware()
    assert platform.exclude_from_capture(12345) is False
    assert platform.register_global_hotkeys(None, {"toggle": "ctrl+alt+t"}, lambda _: None) is False


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 only")
def test_windows_gets_the_win32_implementation():
    from waen.platform.win32 import Win32Platform

    assert isinstance(get_platform(), Win32Platform)


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 only")
def test_make_dpi_aware_is_idempotent():
    platform = get_platform()
    platform.make_dpi_aware()
    platform.make_dpi_aware()


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 only")
@pytest.mark.parametrize(
    "combo,expect_vk",
    [("ctrl+alt+t", ord("T")), ("CTRL+ALT+R", ord("R")), ("ctrl+shift+f5", 0x74)],
)
def test_parse_hotkey_reads_valid_combos(combo, expect_vk):
    from waen.platform.win32 import parse_hotkey

    parsed = parse_hotkey(combo)
    assert parsed is not None
    assert parsed[1] == expect_vk


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 only")
@pytest.mark.parametrize("combo", ["ctrl+alt", "", "ctrl+alt+f99", "++"])
def test_parse_hotkey_rejects_invalid_combos(combo):
    from waen.platform.win32 import parse_hotkey

    assert parse_hotkey(combo) is None
