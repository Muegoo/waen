# Phase 5 — Build notes

- PyInstaller version: not installed; installation was blocked by the sandbox's
  denied PyPI network connection on 2026-09-20.
- Dist size: not available — `dist/waen/` could not be built without PyInstaller.
- First-launch time: not measured — build blocked before executable creation.

## Problems encountered and resolutions

| Problem | Resolution |
|---|---|
| `pyinstaller` was not installed and PyPI connections were blocked (`WinError 10013`). | Added `pyinstaller>=6.0` as the `build` optional dependency. Re-run `.venv\Scripts\python -m pip install -e ".[build]"` in an environment with package access, then build with the included spec. |
| A frozen executable cannot run `sys.executable -c` to probe bettercam. | `DxgiCapture.is_available()` now creates and releases a bettercam camera in-process only when `sys.frozen` is true. |
| WinRT modules and RapidOCR model assets are dynamically loaded. | The spec collects `winrt` submodules and `rapidocr_onnxruntime` data files. |

## SmartScreen / antivirus

- Blocked: not tested; no executable was produced in this sandbox.
- If blocked: distribute the complete onedir folder, inspect the publisher and
  hash, and code-sign a release build when distributing outside a trusted group.

## Required post-build check

Run the following from the project root and confirm exit code 0 plus the chosen
capture backend and OCR engine in its console output:

```bat
dist\waen\waen.exe --region 0,0,64,64 --max-frames 0
```

## ผลการ build จริง (2026-09-20, coordinator)

- `pyinstaller 6.22.3` ติดตั้งใน venv แล้ว build ผ่านใน ~22 s → `dist/waen/` (onedir) **307 MB**, `waen.exe` 7.7 MB
- ปัญหาที่เจอและแก้ในรอบนี้
  1. PyInstaller import ทุก package ใน subprocess เดียวเพื่อหา DLL และ import `winrt.*` ก่อน `onnxruntime`
     → subprocess segfault (ปัญหาเดียวกับ `waen/ocr/__init__.py`) แก้โดย patch ลำดับใน `build/waen.spec`
  2. `waen/__main__.py` ใช้ relative import จึงรันเป็น top-level script ไม่ได้ → เพิ่ม `build/launcher.py`
- ตรวจแล้ว: `waen.exe --region 0,0,64,64 --max-frames 0` exit 0 (เลือก dxgi + windows OCR),
  `waen.exe --cli --region ... --max-frames 2` ทำงาน
- ยังไม่ได้ตรวจ: RapidOCR ใน exe (โมเดล .onnx ถูก collect แล้วแต่ยังไม่ได้รันจริง), การรันบนเครื่องที่ไม่มี Python
