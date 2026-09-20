# Phase 0 — ผลการวัด OCR กับ Persona 5

จำนวนภาพที่ทดสอบ: 15 · จำนวนการวัดทั้งหมด: 120

## คำตัดสิน

**ไม่ผ่าน — หยุด กลับไปคุยกับผู้ใช้**

- ผ่าน: dialogue word accuracy 97.2% (rapid/x2)
- ไม่ผ่าน: latency p95 1545 ms เกิน 400 ms



## ตารางผล

| engine | pipeline | group | word acc | CER | p95 (ms) | n |
|---|---|---|---|---|---|---|
| rapid | invert_x2 | choice | 84.9% | 0.105 | 1495 | 3 |
| rapid | invert_x2 | dialogue | 96.7% | 0.032 | 1440 | 12 |
| rapid | raw | choice | 84.9% | 0.101 | 2161 | 3 |
| rapid | raw | dialogue | 95.8% | 0.035 | 1416 | 12 |
| rapid | x2 | choice | 84.9% | 0.108 | 1624 | 3 |
| rapid | x2 | dialogue | 97.2% | 0.030 | 1545 | 12 |
| rapid | x3_binary | choice | 61.1% | 0.378 | 1273 | 3 |
| rapid | x3_binary | dialogue | 89.0% | 0.078 | 1418 | 12 |
| windows | invert_x2 | choice | 63.0% | 0.324 | 84 | 3 |
| windows | invert_x2 | dialogue | 89.2% | 0.112 | 86 | 12 |
| windows | raw | choice | 66.1% | 0.314 | 27 | 3 |
| windows | raw | dialogue | 89.1% | 0.096 | 24 | 12 |
| windows | x2 | choice | 63.0% | 0.332 | 92 | 3 |
| windows | x2 | dialogue | 89.2% | 0.108 | 84 | 12 |
| windows | x3_binary | choice | 48.7% | 0.522 | 191 | 3 |
| windows | x3_binary | dialogue | 90.2% | 0.114 | 124 | 12 |

## 10 เคสที่แย่ที่สุด

- `choice_03` windows/raw — 35.7% — อ่านได้ว่า: 'want to ask for directions.\noeß\nsorry ,'
- `choice_03` windows/x2 — 35.7% — อ่านได้ว่า: 'want to ask for directions.\nnew\nSorry ,'
- `choice_03` windows/x3_binary — 35.7% — อ่านได้ว่า: '1 want to ask for directions.\nSort Y'
- `choice_03` windows/invert_x2 — 35.7% — อ่านได้ว่า: "want to ask for directions.\noeß\nSort Y '"
- `choice_02` windows/x3_binary — 38.1% — อ่านได้ว่า: 'course\nYou\nWhy do you want to know?'
- `choice_02` rapid/x3_binary — 42.9% — อ่านได้ว่า: "Of course you couldn't..\nWhy do you want to know?"
- `dialogue_10` rapid/x3_binary — 45.5% — อ่านได้ว่า: "下铁脱線事故負傷者80名以\nthe engineer's life was not in danger, despite\nhis injuries."
- `choice_03` rapid/x3_binary — 57.1% — อ่านได้ว่า: 'Want to ask for directions.\nSorry, never mind.'
- `dialogue_02` windows/raw — 66.7% — อ่านได้ว่า: ', NO ce\nStay calm! You can get away now!'
- `dialogue_12` windows/x2 — 68.8% — อ่านได้ว่า: "E eriy fe ale custooer\nWhat could be going on? Didn't\nsomething similar happen just the\nother day?"
