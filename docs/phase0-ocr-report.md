# Phase 0 — ผลการวัด OCR กับ Persona 5 Royal (สรุปและคำตัดสิน)

วัดเมื่อ 2026-09-20 · เครื่อง Windows 11 · ภาพจากเกมจริง 1920×1080 (Borderless) 25 ภาพ
ตารางดิบ: [`phase0-ocr-report-fullframe.md`](phase0-ocr-report-fullframe.md) (ทั้งเฟรม) ·
[`phase0-ocr-report-region.md`](phase0-ocr-report-region.md) (กรอบกล่องบทสนทนา)

## วิธีวัด — ทำไมมีสองรอบ

1. **ทั้งเฟรม** (`tests/fixtures/p5/`, 25 ภาพ): ตามแผนเดิม เฉลยคือทุกข้อความบนจอ
   ผลดีสุด 71.8% — แต่เมื่อไล่ดูรายเคส ตัวบทสนทนาถูกอ่านออกเกือบทั้งหมด คะแนนที่หายไปคือ
   HUD ฟอนต์บิด (MONDAY/Morning), ปุ่ม FFWD/Log, ป้ายภาษาญี่ปุ่นในฉาก, และลำดับบรรทัด
   ซึ่งแอปจริงไม่ได้อ่านเพราะผู้ใช้ลากกรอบเฉพาะกล่องบทสนทนา → วัดคนละคำถามกับ gate
2. **กรอบกล่องบทสนทนา** (`tests/fixtures/p5_region/`, ครอป x 360–1600 y 540–1075 = กรอบที่ผู้ใช้
   จะเลือกจริง, 15 ภาพ `dialogue_`+`choice_`): เฉลยเฉพาะข้อความในกรอบ (ชื่อผู้พูด + บทพูด + ตัวเลือก)

ระหว่างทางแก้ 2 อย่างที่เป็นความผิดของการวัด ไม่ใช่ของ OCR:
- `metrics.normalize` รวมเครื่องหมายแบบพิมพ์สวยกับแบบธรรมดา (`’`→`'`, `—`→`-`, `…`→`...`)
  ก่อนหน้านี้ `couldn’t` กับ `couldn't` ถูกนับผิดทั้งคำ ทั้งที่ไม่ต่างกันสำหรับการแปล
- ตัด `dialogue_03` ออก (ย้ายไป `tests/fixtures/p5_excluded/`) เพราะมี notification ของ Snipping Tool
  ทับกล่องบทสนทนาอยู่ในภาพ

## ผล (กรอบกล่องบทสนทนา, กลุ่ม `dialogue` 12 ภาพ)

| engine / preprocess | word acc รวมชื่อผู้พูด | word acc เฉพาะบทพูด | CER | p95 latency |
|---|---|---|---|---|
| **windows / x3_binary** | 90.2% | **96.4%** | 0.114 | **124 ms** |
| windows / raw | 89.1% | 91.1% | 0.096 | 24 ms |
| **rapid / x2** | **97.2%** | 95.8% | 0.030 | 1,545 ms |
| rapid / raw | 95.8% | — | 0.035 | 1,416 ms |

กลุ่ม `choice` (3 ภาพ, ตัวเลือกเอียงแบบ P5): rapid 80.2% · windows 63.0% — ตัวเลือกอ่านได้แต่ยังหลุดบางบรรทัด
กลุ่ม `menu` (1 ภาพ) ต่ำมากทั้งคู่ (≤ 33%) — เมนูหลักเป็นฟอนต์กราฟิก ไม่ใช่เป้าหมาย v1

## สิ่งที่รู้แล้ว

- **ตัวบทสนทนา (ฟอนต์ในกล่อง) อ่านออกทั้งสอง engine ≥ 95%** — ความเสี่ยงหลักของโปรเจกต์ (สเปกหัวข้อ 3) ตกไป
- **ชื่อผู้พูด** (ฟอนต์ตัดแปะ เช่น "Girl's Voice", "Manager") Windows OCR อ่านไม่ออกและมักคืนขยะ
  (`wxatager`, `, NO ce`) ส่วน RapidOCR อ่านได้ดี
- **latency**: Windows OCR 24–124 ms ผ่านสบาย · RapidOCR บน CPU 1.4–1.5 s ต่อเฟรม ไม่ผ่าน 400 ms
- preprocessing: สำหรับ Windows OCR `x3_binary` ช่วยกรองขยะของชื่อผู้พูดออกได้ (96.4% vs 91.1%)
  โดยยังอยู่ใต้ 400 ms; สำหรับ Rapid `x2` ดีสุดเล็กน้อย

## คำตัดสิน (ต้องให้ผู้ใช้ยืนยัน)

เกณฑ์บังคับ "กล่องบทสนทนา ≥ 95%" **ผ่านเมื่อวัดตัวบทพูด** ด้วย `windows/x3_binary` (96.4%, 124 ms)
และ `rapid/x2` (95.8%, แต่ latency ไม่ผ่าน) — **ไม่มี combo ไหนผ่านทั้งความแม่นรวมชื่อผู้พูดและ latency พร้อมกัน**

ข้อเสนอ: **ไปต่อ** ด้วย Windows OCR + `x3_binary` เป็นค่าเริ่มต้น (แลกกับชื่อผู้พูดที่จะหายหรือเป็นขยะ)
และเก็บ RapidOCR ไว้เป็นตัวเลือกใน config สำหรับคนที่ยอมช้า พร้อมงาน Phase 4 สองข้อ:

1. ตัวกรองบรรทัดขยะจากชื่อผู้พูด (สัดส่วนตัวอักษรที่ไม่ใช่คำ / ไม่มีสระ) ก่อนส่งแปล
2. ลอง `onnxruntime-directml` ให้ RapidOCR ใช้ GPU — ถ้าลงต่ำกว่า 400 ms จะได้ทั้งชื่อผู้พูดและตัวเลือกด้วย

## ชุดข้อมูล

`dialogue` 13 (ใช้ 12 หลังตัด `_03`) · `choice` 3 · `menu` 1 · `mutter` 4 · `fight` 1 · `tutorial` 2 —
ยังขาดตามแผน: `menu` อีก 3, `item` 4, `skew` 3 (`tests/test_fixtures.py` ของ Task 8 จึงยังไม่เพิ่ม)

## DirectML (2026-09-20)

RapidOCR 1.4.4 was configured with `det_use_dml`, `cls_use_dml`, and `rec_use_dml`.
`onnxruntime` reported `DmlExecutionProvider` first for all three sessions, with
`CPUExecutionProvider` available as fallback. The sandbox initialized DirectML without
falling back to CPU.

Command: `.venv\Scripts\python -m scripts.ocr_bakeoff --fixtures tests/fixtures/p5_region --out .pytest-tmp/bakeoff-dml.md`

| rapid dialogue pipeline | word accuracy before → after | p95 latency before → after |
|---|---|---|
| raw | 95.8% → 95.8% | 1,416 ms → 302 ms |
| x2 | 97.2% → 97.2% | 1,545 ms → 1,561 ms |

The raw-input result is substantially faster; x2 did not improve in this run and remains
above the 400 ms latency target.
