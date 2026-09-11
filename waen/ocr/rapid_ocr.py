"""OCR ด้วย RapidOCR (PP-OCR ที่แปลงเป็น ONNX)

ทำไมถึงมีตัวนี้ทั้งที่ Windows มี OCR ในตัว: เป็นตัวเทียบใน Task 9 และเป็น
ทางหนีถ้าเครื่องไม่มี OCR language pack โมเดลคนละตระกูลกันจึงมีโอกาสที่ตัวหนึ่ง
อ่านฟอนต์เกมได้ในขณะที่อีกตัวอ่านไม่ได้

ตัวนี้คืนค่า confidence จริง (reports_confidence = True) จึงกรองด้วย min_score ได้
"""

from __future__ import annotations

import logging

import numpy as np

from ..geometry import Box
from ..models import TextLine

logger = logging.getLogger(__name__)


class RapidOcrEngine:
    name = "rapid"
    reports_confidence = True

    def __init__(self, min_score: float = 0.5) -> None:
        self.min_score = float(min_score)
        self._engine = None

    @classmethod
    def is_available(cls) -> bool:
        try:
            import rapidocr_onnxruntime  # noqa: F401

            return True
        except Exception as exc:
            logger.info("RapidOCR unavailable: %s", exc)
            return False

    def _ensure_engine(self):
        # สร้างแบบขี้เกียจ: การโหลดโมเดล ONNX ใช้เวลาหลายวินาที ไม่ควรเกิดตอน import
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR

            self._engine = RapidOCR()
        return self._engine

    def recognize(self, image: np.ndarray) -> list[TextLine]:
        result, _elapsed = self._ensure_engine()(image)
        if not result:
            return []

        lines: list[TextLine] = []
        for quad, text, score in result:
            confidence = float(score)
            if confidence < self.min_score:
                continue
            text = text.strip()
            if not text:
                continue
            # โมเดลคืนสี่เหลี่ยมสี่มุมซึ่งอาจเอียง เราแปลงเป็นกล่องตั้งฉาก
            # เพราะชั้นวาดของเราวาดแนวนอนอย่างเดียว
            xs = [float(point[0]) for point in quad]
            ys = [float(point[1]) for point in quad]
            box = Box(
                int(min(xs)),
                int(min(ys)),
                max(1, int(max(xs) - min(xs))),
                max(1, int(max(ys) - min(ys))),
            )
            lines.append(TextLine(text=text, box=box, confidence=confidence))
        return lines

    def close(self) -> None:
        self._engine = None
