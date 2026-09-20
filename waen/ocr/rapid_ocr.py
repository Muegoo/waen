"""OCR ด้วย RapidOCR (PP-OCR ที่แปลงเป็น ONNX)

ทำไมถึงมีตัวนี้ทั้งที่ Windows มี OCR ในตัว: เป็นตัวเทียบใน Task 9 และเป็น
ทางหนีถ้าเครื่องไม่มี OCR language pack โมเดลคนละตระกูลกันจึงมีโอกาสที่ตัวหนึ่ง
อ่านฟอนต์เกมได้ในขณะที่อีกตัวอ่านไม่ได้

ตัวนี้คืนค่า confidence จริง (reports_confidence = True) จึงกรองด้วย min_score ได้
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np

from ..geometry import Box
from ..models import TextLine

logger = logging.getLogger(__name__)

CPU_PROVIDER = "CPUExecutionProvider"
CUDA_PROVIDER = "CUDAExecutionProvider"
DIRECTML_PROVIDER = "DmlExecutionProvider"


class RapidOcrEngine:
    name = "rapid"
    reports_confidence = True

    def __init__(
        self,
        min_score: float = 0.5,
        providers: Sequence[str] | None = None,
    ) -> None:
        self.min_score = float(min_score)
        self.providers = (
            tuple(providers) if providers is not None else self._auto_providers()
        )
        self.active_providers: tuple[str, ...] = ()
        self._engine = None

    @staticmethod
    def _auto_providers() -> tuple[str, ...]:
        try:
            from onnxruntime import get_available_providers

            available = get_available_providers()
        except Exception as exc:
            logger.info("ONNX Runtime providers unavailable; using CPU: %s", exc)
            return (CPU_PROVIDER,)

        if DIRECTML_PROVIDER in available:
            return (DIRECTML_PROVIDER, CPU_PROVIDER)
        return (CPU_PROVIDER,)

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

            try:
                self._engine = RapidOCR(**self._rapidocr_kwargs(self.providers))
            except Exception as exc:
                if DIRECTML_PROVIDER not in self.providers:
                    raise
                logger.warning(
                    "RapidOCR DirectML initialisation failed (%s); retrying on CPU", exc
                )
                self._engine = RapidOCR(**self._rapidocr_kwargs((CPU_PROVIDER,)))
                self.active_providers = (CPU_PROVIDER,)
            else:
                self.active_providers = self._session_providers() or self.providers
            logger.info("RapidOCR active providers: %s", self.active_providers)
        return self._engine

    @staticmethod
    def _rapidocr_kwargs(providers: Sequence[str]) -> dict[str, bool]:
        """Map ONNX Runtime providers to RapidOCR 1.4's per-model flags."""
        use_dml = DIRECTML_PROVIDER in providers
        use_cuda = CUDA_PROVIDER in providers
        return {
            "det_use_dml": use_dml,
            "cls_use_dml": use_dml,
            "rec_use_dml": use_dml,
            "det_use_cuda": use_cuda,
            "cls_use_cuda": use_cuda,
            "rec_use_cuda": use_cuda,
        }

    def _session_providers(self) -> tuple[str, ...]:
        """Return providers reported by each RapidOCR ONNX session, if exposed."""
        providers: list[str] = []
        for component, attribute in (
            ("text_det", "infer"),
            ("text_cls", "infer"),
            ("text_rec", "session"),
        ):
            infer = getattr(getattr(self._engine, component, None), attribute, None)
            session = getattr(infer, "session", None)
            get_providers = getattr(session, "get_providers", None)
            if get_providers is not None:
                providers.extend(get_providers())
        return tuple(dict.fromkeys(providers))

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
