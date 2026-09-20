# Phase 0 — ผลการวัด OCR กับ Persona 5

จำนวนภาพที่ทดสอบ: 25 · จำนวนการวัดทั้งหมด: 200

## คำตัดสิน

**ไม่ผ่าน — หยุด กลับไปคุยกับผู้ใช้**

- ไม่ผ่าน: dialogue word accuracy ดีที่สุดคือ 71.8% (rapid/x2) ต้องได้ 95%
- ไม่ผ่าน: latency p95 1649 ms เกิน 400 ms
- ต่ำกว่าเป้า (ไม่บล็อก): menu word accuracy 27.8%



## ตารางผล

| engine | pipeline | group | word acc | CER | p95 (ms) | n |
|---|---|---|---|---|---|---|
| rapid | invert_x2 | choice | 72.4% | 0.112 | 1761 | 3 |
| rapid | invert_x2 | dialogue | 71.5% | 0.130 | 1711 | 14 |
| rapid | invert_x2 | fight | 44.8% | 0.403 | 1695 | 1 |
| rapid | invert_x2 | menu | 33.3% | 0.553 | 1578 | 1 |
| rapid | invert_x2 | mutter | 53.2% | 0.330 | 1795 | 4 |
| rapid | invert_x2 | tutorial | 82.7% | 0.049 | 1578 | 2 |
| rapid | raw | choice | 73.9% | 0.120 | 2600 | 3 |
| rapid | raw | dialogue | 69.9% | 0.142 | 1657 | 14 |
| rapid | raw | fight | 48.3% | 0.369 | 1673 | 1 |
| rapid | raw | menu | 16.7% | 0.602 | 1576 | 1 |
| rapid | raw | mutter | 48.3% | 0.359 | 1784 | 4 |
| rapid | raw | tutorial | 86.9% | 0.036 | 1617 | 2 |
| rapid | x2 | choice | 74.3% | 0.116 | 1992 | 3 |
| rapid | x2 | dialogue | 71.8% | 0.146 | 1649 | 14 |
| rapid | x2 | fight | 44.8% | 0.392 | 1603 | 1 |
| rapid | x2 | menu | 27.8% | 0.621 | 1559 | 1 |
| rapid | x2 | mutter | 57.2% | 0.286 | 1807 | 4 |
| rapid | x2 | tutorial | 84.3% | 0.050 | 1712 | 2 |
| rapid | x3_binary | choice | 45.8% | 0.445 | 1433 | 3 |
| rapid | x3_binary | dialogue | 63.8% | 0.174 | 1432 | 14 |
| rapid | x3_binary | fight | 41.4% | 0.347 | 1101 | 1 |
| rapid | x3_binary | menu | 16.7% | 0.573 | 1288 | 1 |
| rapid | x3_binary | mutter | 56.5% | 0.278 | 1561 | 4 |
| rapid | x3_binary | tutorial | 78.5% | 0.192 | 1356 | 2 |
| windows | invert_x2 | choice | 57.4% | 0.392 | 267 | 3 |
| windows | invert_x2 | dialogue | 57.2% | 0.351 | 273 | 14 |
| windows | invert_x2 | fight | 0.0% | 0.778 | 231 | 1 |
| windows | invert_x2 | menu | 16.7% | 0.602 | 162 | 1 |
| windows | invert_x2 | mutter | 60.2% | 0.336 | 328 | 4 |
| windows | invert_x2 | tutorial | 66.0% | 0.370 | 155 | 2 |
| windows | raw | choice | 50.0% | 0.404 | 129 | 3 |
| windows | raw | dialogue | 56.9% | 0.346 | 104 | 14 |
| windows | raw | fight | 24.1% | 0.631 | 109 | 1 |
| windows | raw | menu | 5.6% | 0.738 | 48 | 1 |
| windows | raw | mutter | 58.8% | 0.341 | 92 | 4 |
| windows | raw | tutorial | 70.7% | 0.326 | 39 | 2 |
| windows | x2 | choice | 57.4% | 0.389 | 276 | 3 |
| windows | x2 | dialogue | 59.9% | 0.332 | 297 | 14 |
| windows | x2 | fight | 13.8% | 0.659 | 260 | 1 |
| windows | x2 | menu | 11.1% | 0.602 | 183 | 1 |
| windows | x2 | mutter | 60.2% | 0.334 | 318 | 4 |
| windows | x2 | tutorial | 66.0% | 0.370 | 140 | 2 |
| windows | x3_binary | choice | 38.6% | 0.604 | 547 | 3 |
| windows | x3_binary | dialogue | 53.7% | 0.389 | 500 | 14 |
| windows | x3_binary | fight | 27.6% | 0.636 | 409 | 1 |
| windows | x3_binary | menu | 27.8% | 0.660 | 372 | 1 |
| windows | x3_binary | mutter | 51.5% | 0.388 | 795 | 4 |
| windows | x3_binary | tutorial | 77.0% | 0.246 | 281 | 2 |

## 10 เคสที่แย่ที่สุด

- `dialogue_01` windows/x3_binary — 0.0% — อ่านได้ว่า: "SmilmffesbetwZ'1\nlivirgHnyourwddaeptrelycoh'1dd8'1bI"
- `dialogue_03` windows/x3_binary — 0.0% — อ่านได้ว่า: 'Gace\nHm...? What was that\n-•—lr•HW\nS" aping Taal\nScreens •10t copiec to crpboa rcl'
- `dialogue_01` windows/invert_x2 — 0.0% — อ่านได้ว่า: 'Smilaiåes'
- `fight_01` windows/invert_x2 — 0.0% — อ่านได้ว่า: "keepe\npyre\nficia\nSacri\nTagewAim\nTab Rush\nin\nGUARD\nComparing power levels...\nNo threat. Get 'em, Joker!\n9)\nY..LZ'"
- `mutter_04` windows/x3_binary — 4.2% — อ่านได้ว่า: "Whoa, hey, is it raining?\nB Log Tab Meu\nLive an honest student life\nGo to Shujin Academy\nfüä'll-filfildkh_\nAoyama-Itc\nsu"
- `mutter_04` rapid/raw — 4.2% — อ่านได้ว่า: 'Live an honest student life\nMONDaY\nGo to Shujin Academy\n冻坡兒附\nEarly\n意山一丁目箱\nMorning\nHATER\nNoyama\n電車\nTrain Approaching\n(C+t'
- `dialogue_01` windows/raw — 4.3% — อ่านได้ว่า: 'Smnaiåesbetweel to'
- `menu_01` windows/raw — 5.6% — อ่านได้ว่า: 'NwwGME\nO ATL US. @SEGA. All rights reserved.\nIADGßME\nC.DNFEG'
- `dialogue_03` windows/raw — 7.7% — อ่านได้ว่า: 'Snipping Tool\nScreenshot copied to clipboard\nAuto I\nHm...? What was that...?'
- `choice_03` windows/raw — 11.1% — อ่านได้ว่า: 'Qot\nunfriendly Offåcer\necti\nSorry, never mind'
