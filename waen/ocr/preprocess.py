"""เตรียมภาพก่อนส่งเข้า OCR

ทุกฟังก์ชันรับและคืนภาพ BGR uint8 รูปร่าง (H, W, 3) เพื่อให้ต่อกันได้อิสระ
และเพื่อให้ OCR engine ทุกตัวรับ input รูปแบบเดียวเสมอ

ใช้ numpy ล้วน ไม่พึ่ง OpenCV เพราะทั้งโปรเจกต์ไม่ได้ต้องการ OpenCV ที่อื่นเลย
และการลดจำนวน dependency ทำให้ build .exe เล็กลงมาก
"""

from __future__ import annotations

from typing import Callable

import numpy as np


def upscale(image: np.ndarray, factor: int) -> np.ndarray:
    """ขยายภาพแบบ nearest-neighbour

    เจตนาใช้ nearest ไม่ใช่การ interpolate เพราะขอบตัวอักษรที่คมช่วย OCR
    ได้มากกว่าขอบที่ถูกเกลี่ยให้เบลอ
    """
    if factor < 1:
        raise ValueError("factor must be >= 1")
    if factor == 1:
        return image
    return np.repeat(np.repeat(image, factor, axis=0), factor, axis=1)


def to_gray(image: np.ndarray) -> np.ndarray:
    """BGR -> grayscale ด้วยน้ำหนัก ITU-R BT.601"""
    b, g, r = image[:, :, 0], image[:, :, 1], image[:, :, 2]
    return (0.114 * b + 0.587 * g + 0.299 * r).astype(np.uint8)


def _otsu_threshold(gray: np.ndarray) -> int:
    """หา threshold ที่แยกพื้นหน้า/พื้นหลังได้ดีที่สุดตามวิธี Otsu"""
    hist = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    total = gray.size
    weight_bg = np.cumsum(hist)
    weight_fg = total - weight_bg
    intensity = np.cumsum(hist * np.arange(256))
    mean_total = intensity[-1]

    valid = (weight_bg > 0) & (weight_fg > 0)
    mean_bg = np.zeros(256)
    mean_fg = np.zeros(256)
    mean_bg[valid] = intensity[valid] / weight_bg[valid]
    mean_fg[valid] = (mean_total - intensity[valid]) / weight_fg[valid]

    between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
    between[~valid] = -1.0
    return int(np.argmax(between))


def binarize(image: np.ndarray) -> np.ndarray:
    gray = to_gray(image)
    threshold = _otsu_threshold(gray)
    mask = np.where(gray > threshold, 255, 0).astype(np.uint8)
    return np.repeat(mask[:, :, None], 3, axis=2)


def invert(image: np.ndarray) -> np.ndarray:
    return (255 - image).astype(np.uint8)


PIPELINES: dict[str, Callable[[np.ndarray], np.ndarray]] = {
    "raw": lambda img: img,
    "x2": lambda img: upscale(img, 2),
    "x3_binary": lambda img: binarize(upscale(img, 3)),
    "invert_x2": lambda img: upscale(invert(img), 2),
}

_SCALE_FACTORS: dict[str, int] = {
    "raw": 1,
    "x2": 2,
    "x3_binary": 3,
    "invert_x2": 2,
}


def scale_factor_of(name: str) -> int:
    """pipeline นั้นขยายภาพกี่เท่า

    ผู้เรียกต้องหารกล่องที่ OCR คืนมาด้วยค่านี้เพื่อกลับสู่พิกัดของภาพต้นฉบับ
    ลืมข้อนี้แล้วคำแปลจะไปวาดผิดตำแหน่งทั้งหมด
    """
    return _SCALE_FACTORS[name]
