"""เลือก OCR engine ตามที่ตั้งค่าไว้ พร้อมทางหนี"""

from __future__ import annotations

import logging

from .base import OcrEngine
from .rapid_ocr import RapidOcrEngine
from .windows_ocr import WindowsOcrEngine

logger = logging.getLogger(__name__)

VALID_PREFERENCES = ("auto", "windows", "rapid")


def create_engine(preference: str = "auto") -> OcrEngine:
    if preference not in VALID_PREFERENCES:
        raise ValueError(
            f"ไม่รู้จัก ocr_engine {preference!r} — ต้องเป็นหนึ่งใน {VALID_PREFERENCES}"
        )

    if preference == "windows":
        return WindowsOcrEngine()
    if preference == "rapid":
        return RapidOcrEngine()

    if WindowsOcrEngine.is_available():
        logger.info("OCR engine: windows")
        return WindowsOcrEngine()
    if RapidOcrEngine.is_available():
        logger.info("OCR engine: rapid (Windows OCR ใช้ไม่ได้)")
        return RapidOcrEngine()

    raise RuntimeError(
        "ไม่มี OCR engine ที่ใช้งานได้ — ติดตั้ง English OCR language pack "
        "ใน Windows Settings หรือรัน pip install rapidocr-onnxruntime"
    )
