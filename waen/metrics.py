"""วัดความแม่นยำ OCR

ตัวเลขจากไฟล์นี้เป็นตัวตัดสินว่าโปรเจกต์เดินต่อหรือหยุด จึงเขียนแบบตรงไปตรงมา
ที่สุดและมีเทสครอบทุกเส้น ไม่พึ่ง library ภายนอกเพื่อให้ตรวจสอบได้ด้วยตาเปล่า
"""

from __future__ import annotations

import re
from typing import Sequence

_WHITESPACE = re.compile(r"\s+")

# เครื่องหมายแบบพิมพ์สวย (typographic) ที่ OCR มักคืนเป็นแบบธรรมดา — ต่างกันแค่รูป
# ไม่ต่างความหมาย ถ้าไม่รวมเป็นตัวเดียวกัน คำทั้งคำเช่น couldn’t จะถูกนับว่าผิด
_TYPOGRAPHY = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "′": "'",
    "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-", "―": "-", "−": "-",
    "…": "...",
})


def normalize(text: str) -> str:
    """ทำให้เทียบกันได้ยุติธรรม: ยุบช่องว่าง ตัดหัวท้าย ไม่สนตัวพิมพ์

    เจตนา *ไม่* ตัดเครื่องหมายวรรคตอนออก เพราะจุลภาคกับเครื่องหมายคำถาม
    เปลี่ยนความหมายของประโยคที่จะถูกส่งไปแปล
    """
    return _WHITESPACE.sub(" ", text.translate(_TYPOGRAPHY)).strip().casefold()


def levenshtein(a: Sequence, b: Sequence) -> int:
    """ระยะแก้ไข ใช้ได้ทั้งกับสตริง (ระดับตัวอักษร) และลิสต์ของคำ"""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)

    previous = list(range(len(b) + 1))
    for i, item_a in enumerate(a, start=1):
        current = [i]
        for j, item_b in enumerate(b, start=1):
            current.append(
                min(
                    previous[j] + 1,  # ลบ
                    current[j - 1] + 1,  # เพิ่ม
                    previous[j - 1] + (item_a != item_b),  # แทนที่
                )
            )
        previous = current
    return previous[-1]


def word_accuracy(truth: str, hypothesis: str) -> float:
    """สัดส่วนคำที่ถูก คิดจากระยะแก้ไขระดับคำ ไม่ต่ำกว่า 0.0"""
    truth_words = normalize(truth).split()
    hypothesis_words = normalize(hypothesis).split()
    if not truth_words:
        return 1.0 if not hypothesis_words else 0.0
    errors = levenshtein(truth_words, hypothesis_words)
    return max(0.0, 1.0 - errors / len(truth_words))


def character_error_rate(truth: str, hypothesis: str) -> float:
    """ระยะแก้ไขระดับตัวอักษรหารด้วยความยาวจริง เกิน 1.0 ได้ถ้า OCR แถมข้อความมา"""
    truth_text = normalize(truth)
    hypothesis_text = normalize(hypothesis)
    if not truth_text:
        return 0.0 if not hypothesis_text else float(len(hypothesis_text))
    return levenshtein(truth_text, hypothesis_text) / len(truth_text)
