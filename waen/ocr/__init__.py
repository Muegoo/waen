"""OCR engines.

IMPORTANT — import order: ``onnxruntime`` must be loaded *before* any ``winrt.*``
module, otherwise the process segfaults on this machine (verified 2026-09-11 with
onnxruntime 1.30.0 + winrt-runtime 3.2.1 on Python 3.12). Loading it here
guarantees the order no matter which engine module is imported first.
"""

try:
    import onnxruntime  # noqa: F401
except ImportError:  # RapidOCR not installed — Windows OCR alone is fine
    pass
