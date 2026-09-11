"""Command-line entry point for the coordinate-verification capture mode."""

from __future__ import annotations

import argparse
import sys

from .geometry import Box


def _select_region() -> tuple[Box, float] | None:
    """Show the selector and return its physical-pixel result, if any."""
    from PyQt6.QtGui import QGuiApplication
    from PyQt6.QtWidgets import QApplication

    from .platform import get_platform
    from .ui.region_selector import RegionSelector

    platform = get_platform()
    platform.make_dpi_aware()  # Must precede QApplication construction.

    app = QApplication(sys.argv)
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        print("No display is available for region selection.")
        return None

    virtual = screen.virtualGeometry()
    dpr = screen.devicePixelRatio()
    print(f"virtual geometry (logical) = {virtual}, devicePixelRatio = {dpr}")
    result: dict[str, Box | float] = {}

    def on_selected(box: Box, scale: float) -> None:
        result["box"] = box
        result["scale"] = scale
        app.quit()

    selector = RegionSelector(virtual, dpr)
    selector.selected.connect(on_selected)
    selector.cancelled.connect(app.quit)
    selector.showFullScreen()
    app.exec()

    box = result.get("box")
    scale = result.get("scale")
    if not isinstance(box, Box) or not isinstance(scale, float):
        return None
    return box, scale


def _capture_region(output_path: str, box: Box, capture_backend: str) -> int:
    """Capture ``box`` and save it as an RGB PNG."""
    from PyQt6.QtGui import QImage

    from .capture.factory import create_backend

    backend = create_backend(capture_backend)
    try:
        frame = None
        for _ in range(10):
            frame = backend.grab(box)
            if frame is not None:
                break
        if frame is None:
            print("Unable to capture the selected region.")
            return 2

        height, width = frame.shape[:2]
        rgb = frame[:, :, ::-1].copy()
        image = QImage(rgb.data, width, height, width * 3, QImage.Format.Format_RGB888)
        if not image.save(output_path):
            print(f"Unable to save PNG: {output_path}")
            return 3
        print(f"Saved: {output_path} ({width}x{height})")
    finally:
        backend.close()
    return 0


def _save_region(output_path: str) -> int:
    from .config import load_config, save_config

    config = load_config()
    box = config.region_box()
    if box is None:
        selected = _select_region()
        if selected is None:
            print("Region selection cancelled.")
            return 1
        box, scale = selected
        print(f"Selected region (physical) = {box}")
        config.set_region(box, scale)
        save_config(config)
    else:
        print(f"Using saved region (physical) = {box}")

    return _capture_region(output_path, box, config.capture_backend)


def main() -> int:
    parser = argparse.ArgumentParser(prog="waen", description="On-screen game translator")
    parser.add_argument(
        "--save-region",
        metavar="OUT.PNG",
        help="select a region (or use the saved one) and save one capture as a PNG",
    )
    args = parser.parse_args()

    if args.save_region:
        return _save_region(args.save_region)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
