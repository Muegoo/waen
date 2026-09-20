# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir build for waen.

RapidOCR's ONNX models live in its installed package, so they must be copied as
data files. WinRT bindings are dynamically imported by the Windows OCR engine,
which requires collecting the namespace's submodules explicitly.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import PyInstaller.building.build_main as _build_main

# PyInstaller imports every collected package in one isolated subprocess to find
# binary dependencies. Importing winrt.* before onnxruntime segfaults that
# subprocess (same hazard waen/ocr/__init__.py guards against), so force
# onnxruntime to the front of the import list.
_find_binary_dependencies = _build_main.find_binary_dependencies


def _find_binary_dependencies_onnx_first(binaries, import_packages, *args, **kwargs):
    onnx = [pkg for pkg in import_packages if pkg.split(".")[0] == "onnxruntime"]
    rest = [pkg for pkg in import_packages if pkg.split(".")[0] != "onnxruntime"]
    return _find_binary_dependencies(binaries, onnx + rest, *args, **kwargs)


_build_main.find_binary_dependencies = _find_binary_dependencies_onnx_first


PROJECT_ROOT = Path(SPECPATH).parent

datas = [(str(PROJECT_ROOT / "glossary"), "glossary")]
try:
    datas += collect_data_files("rapidocr_onnxruntime")
except Exception:
    # Windows OCR remains usable when the optional RapidOCR package is absent.
    pass

hiddenimports = [
    "bettercam",
    "mss",
    "deep_translator",
    "rapidocr_onnxruntime",
    *collect_submodules("winrt"),
]

a = Analysis(
    [str(PROJECT_ROOT / "build" / "launcher.py")],
    pathex=[str(PROJECT_ROOT)],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=["tkinter", "matplotlib", "pytest"],
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="waen",
    console=True,
    icon=None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="waen")
