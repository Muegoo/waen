# AGENTS.md — brief for coding agents working on waen

You are one of several agents implementing this project in parallel. A coordinator
assigns you **one task at a time** from the implementation plan and reviews your work.

## Source of truth

- Spec: `docs/superpowers/specs/2026-09-10-waen-design.md`
- Plan: `docs/superpowers/plans/2026-09-10-waen.md` — find your task with
  `grep -n "^### Task <N>:" docs/superpowers/plans/2026-09-10-waen.md` and read from
  that heading to the next `### Task` heading. **Follow its steps in order (TDD:
  failing test → implementation → passing test → commit).** The plan's code is the
  reference implementation; deviate only when it is wrong on this machine, and say so
  in your final report.
- The "Global Constraints" section at the top of the plan applies to every task.

## Environment (already set up — do NOT reinstall or create venvs)

- Windows 11, **Python 3.12** venv at `.venv` in this working directory.
- Run everything through the venv: `.venv\Scripts\python -m pytest ...`,
  `.venv\Scripts\python -m waen ...`, `.venv\Scripts\python scripts\x.py`.
- All dependencies from `pyproject.toml` are installed. No network install needed.
  If you truly need a new package, stop and report it instead of installing.
- **winsdk is NOT used** (no Python 3.12 build). Use the `winrt-*` packages:
  `from winrt.windows.media.ocr import OcrEngine`, `from winrt.windows.globalization
  import Language`, `from winrt.windows.graphics.imaging import SoftwareBitmap,
  BitmapPixelFormat, BitmapAlphaMode`, `from winrt.windows.security.cryptography
  import CryptographicBuffer`. Wherever the plan says `winsdk.windows.X`, use
  `winrt.windows.X`.
- **Import-order hazard:** importing any `winrt.*` module before `onnxruntime`
  segfaults the process. `waen/ocr/__init__.py` already preloads onnxruntime — keep
  that, and never import `winrt` from a module outside `waen.ocr` without importing
  `waen.ocr` first.
- Windows OCR language packs available: `en-US`, `en-GB`. RapidOCR models are
  downloaded already.
- Qt tests: `tests/conftest.py` sets `QT_QPA_PLATFORM=offscreen`; use the `qt_app`
  fixture (created in Task 5).

## Git rules

- You are on your own branch in your own git worktree. Commit on it freely, one commit
  per task (or per green unit, as the plan says). Use the commit message from the plan.
- **Never** run `git push`, `git merge`, `git rebase`, `git checkout <other-branch>`,
  or touch `main`. The coordinator merges.
- Only touch the files listed under **Files:** for your task (plus `__init__.py`
  exports if the plan says so). Do not "improve" other modules.
- Do not commit anything under `tests/fixtures/p5/`, `corpus/`, or `debug_dump/`
  unless your task explicitly creates them.

## Definition of done — put this in your final message

1. Task number and the commit hash(es).
2. Output of the **full** suite: `.venv\Scripts\python -m pytest -q` (must be green;
   skips are fine only for reasons the plan allows).
3. Any deviation from the plan and why.
4. Anything the next task needs to know (API differences, gotchas, measured numbers).

Keep the report short. No summaries of the plan back to the coordinator.
