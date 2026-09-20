"""Command-line entry point for the coordinate-verification capture mode."""

from __future__ import annotations

import argparse
import sys

from .geometry import Box


def _run_cli(
    region_arg: str | None,
    max_frames: int | None = None,
    dumper=None,
) -> int:
    """Capture, translate, and print text without constructing an overlay UI."""
    import time

    from .capture.factory import create_backend
    from .config import load_config
    from .ocr.factory import create_engine
    from .pipeline.core import PipelineCore
    from .platform import get_platform
    from .translate.glossary import Glossary
    from .translate.google import GoogleTranslateBackend

    if max_frames is not None and max_frames < 0:
        print("--max-frames must be zero or greater.")
        return 2

    get_platform().make_dpi_aware()
    config = load_config()
    if region_arg:
        try:
            x, y, w, h = (int(part) for part in region_arg.split(","))
            region = Box(x, y, w, h)
        except ValueError:
            print("--region must be x,y,w,h using integer physical pixels.")
            return 2
    else:
        region = config.region_box()
    if region is None:
        print("No region selected; run --save-region or pass --region x,y,w,h.")
        return 1

    ocr = create_engine(config.ocr_engine)
    core = PipelineCore(
        ocr=ocr,
        config=config,
        glossary=Glossary.from_file(config.glossary_path),
        preprocess_name=config.preprocess,
        translator=GoogleTranslateBackend(config.source_lang, config.target_lang),
    )
    backend = create_backend(config.capture_backend)
    print(
        f"Watching {region} with capture backend {backend.name} "
        f"and OCR engine {ocr.name} — Ctrl+C to stop"
    )

    frames_seen = 0
    try:
        while max_frames is None or frames_seen < max_frames:
            frame = backend.grab(region)
            if frame is not None:
                now_ms = int(time.monotonic() * 1000)
                started = time.perf_counter()
                blocks = core.detect(frame, (region.x, region.y), now_ms)
                detect_ms = (time.perf_counter() - started) * 1000.0
                lines = list(core.last_lines)
                started = time.perf_counter()
                translated = []
                for block in blocks:
                    result = core.translate(block)
                    print(f"\n[{block.kind}] {block.source_text}")
                    if result is None:
                        print("  -> translation failed")
                    else:
                        translated.append(result)
                        flag = "" if result.glossary_applied else "  (glossary not applied)"
                        print(f"  -> {result.translated}{flag}")
                if dumper is not None and blocks:
                    dumper.dump(
                        frame,
                        lines,
                        blocks,
                        translated,
                        {
                            "detect_ms": round(detect_ms, 1),
                            "translate_ms": round(
                                (time.perf_counter() - started) * 1000.0, 1
                            ),
                        },
                        region,
                    )
                frames_seen += 1
            time.sleep(config.poll_interval_ms / 1000)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        backend.close()
    return 0


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
    # คอนโซล Windows เป็น cp1252 โดยปริยาย พิมพ์คำแปลไทยแล้วล้ม จึงบังคับ UTF-8
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="waen", description="On-screen game translator")
    parser.add_argument(
        "--save-region",
        metavar="OUT.PNG",
        help="select a region (or use the saved one) and save one capture as a PNG",
    )
    parser.add_argument("--cli", action="store_true", help="terminal mode without overlay")
    parser.add_argument(
        "--region", help="skip selection: x,y,w,h in physical pixels"
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        help="exit CLI mode after this many non-empty captured frames",
    )
    parser.add_argument(
        "--debug-dump",
        metavar="DIR",
        help="write a bounded ring of frame, box, and pipeline debug snapshots",
    )
    args = parser.parse_args()

    dumper = None
    if args.debug_dump:
        from .debug import DebugDumper

        dumper = DebugDumper(args.debug_dump)

    if args.cli:
        return _run_cli(args.region, args.max_frames, dumper)

    if args.save_region:
        return _save_region(args.save_region)

    from .app import main as run_app
    from .config import load_config
    from .pipeline.worker import set_default_dumper

    config = load_config()
    if args.region:
        try:
            x, y, w, h = (int(part) for part in args.region.split(","))
            config.set_region(Box(x, y, w, h), scale=1.0)
        except ValueError:
            print("--region must be x,y,w,h using integer physical pixels.")
            return 2
    set_default_dumper(dumper)
    return run_app(config=config, max_frames=args.max_frames)


if __name__ == "__main__":
    raise SystemExit(main())
