# waen (แว่น) — แว่นแปลหน้าจอสำหรับเล่นเกม

เอกสารออกแบบ (Design Spec) · 2026-09-10 · แก้ไข 2026-09-11 (เพิ่มหัวข้อ 16)
Target: **Windows 10 (2004+) / 11** · **Python 3.11+** · เป้าหมายแรก: **Persona 5 Royal (PC)**

---

## 1. ปัญหาและเป้าหมาย

เล่นเกมภาษาอังกฤษแล้วอ่านบางจุดไม่เข้าใจ การสลับไปเปิดตัวแปลทำให้เสียอรรถรส
ต้องการโปรแกรมที่เฝ้าดูพื้นที่บนหน้าจอ แล้วแสดงคำแปลไทย **ลอยเหนือข้อความต้นฉบับ
โดยไม่บังต้นฉบับ** เพราะผู้ใช้ยังต้องการเห็นว่าคำแปลนั้นมาจากคำว่าอะไร

### สิ่งที่ต้องทำได้ (v1)

1. เลือกพื้นที่บนหน้าจอที่ต้องการเฝ้า
2. ตรวจจับว่าข้อความในพื้นที่นั้นเปลี่ยน แล้ว OCR **พร้อมพิกัดกล่องของแต่ละบรรทัด**
3. แปลอังกฤษ → ไทย
4. วาดคำแปลเป็น overlay ลอยบนสุด คลิกทะลุ **เหนือข้อความต้นฉบับ ไม่บังต้นฉบับ**
5. ทำงานกับเกมโหมด **Borderless windowed** (ดูรายละเอียดข้อจำกัด fullscreen ในหัวข้อ 9)
6. โปรแกรมต้องไม่จับภาพคำแปลของตัวเองมาแปลซ้ำ

### สิ่งที่ไม่ทำใน v1 (Non-goals)

- ภาษาอื่นนอกจาก en → th (แต่ interface ออกแบบเผื่อไว้)
- แปลเสียงพูด / ซับไตเติลวิดีโอ
- แก้ไฟล์เกม, mod, หรือ hook DirectX/Vulkan
  (การ**อ่าน**ไฟล์เกมเพื่อดึงบทพูดในหัวข้อ 16 ไม่นับ เพราะไม่แก้อะไรในเกม)
- macOS / Linux (โครงสร้าง platform layer แยกไว้แล้ว แต่ implement เฉพาะ Windows)
- แปลด้วย LLM/API แบบเสียเงิน**ตอนเล่น** — runtime ใช้ Google ฟรีอย่างเดียว
  (การจ่ายครั้งเดียวตอนสร้างคลังแปลล่วงหน้าเป็นเรื่องของ v1.5 หัวข้อ 16 ไม่บล็อก v1)

---

## 2. บริบท: ทำไมไม่ใช้ `scan2translate` เดิม

มีโปรเจกต์เดิมชื่อ `scan2translate` (~1,600 บรรทัด, ก.ค. 2026) ที่แก้ปัญหาใกล้เคียงกัน
แต่ต่างกัน 3 จุดที่ลึกถึงระดับ pipeline:

| | scan2translate | waen |
|---|---|---|
| ผลลัพธ์ OCR | ทิ้ง bounding box (`for _box, text, score in result`) ใช้แต่ text | **box คือข้อมูลหลัก** เดินทางไปจนถึงชั้นวาด |
| การวางคำแปล | กล่องเดียวคลุมทั้งกรอบ หรือแถบล่าง | ต่อกลุ่มข้อความ วางเหนือ anchor ของกลุ่มนั้น |
| การจับภาพ | mss (GDI) — README ระบุเองว่า exclusive fullscreen ได้จอดำ | DXGI Desktop Duplication เป็นหลัก mss เป็น fallback |
| สถานะการทดสอบ | เขียนบน macOS, checklist Windows 7 ข้อ ยังไม่ติ๊กสักข้อ | พัฒนาและทดสอบบน Windows ตั้งแต่ Phase 0 |

**ตัดสินใจ:** สร้างโปรเจกต์ใหม่ในโฟลเดอร์ `waen` แล้ว **ยกโค้ดส่วนที่พิสูจน์แล้วว่าถูกมาใช้ต่อ**

### สิ่งที่ยกมาจาก scan2translate

| ไฟล์เดิม | ยกมาเป็น | สภาพ |
|---|---|---|
| `platform/win32.py` | `waen/platform/win32.py` | ใช้เกือบทั้งดุ้น — DPI awareness, `WDA_EXCLUDEFROMCAPTURE`, `RegisterHotKey` + `WM_HOTKEY` filter, `parse_hotkey()` |
| `core/detection.py` | `waen/pipeline/framediff.py` | ใช้ได้ตามเดิม |
| `core/debounce.py` | `waen/pipeline/stabilize.py` | เป็นฐาน แต่เพิ่มกฎ prefix-growth (หัวข้อ 6) |
| `config.py` | `waen/config.py` | รูปแบบ JSON + path ต่อ OS ใช้ได้ ปรับ schema |
| `ui/region_selector.py` | `waen/ui/region_selector.py` | เป็นฐาน แยกส่วนคำนวณพิกัดออกไป `geometry.py` |
| `core/translate.py` | `waen/translate/google.py` | เป็นฐาน เพิ่ม rate limit + batching |
| `core/capture.py` | `waen/capture/mss_backend.py` | ลดบทบาทเป็น fallback |
| `core/ocr.py` | — | **เขียนใหม่** ต้องคืน box |
| `ui/overlay.py` | — | **เขียนใหม่** ต้องวาดหลายกล่อง |
| `ui/worker.py` | — | **เขียนใหม่** ต้องส่ง box ผ่าน pipeline |

---

## 3. ความเสี่ยงหลัก และ Phase 0 ที่เป็นประตูตัดสิน

**ความเสี่ยงที่ทำให้โปรเจกต์ล้มทั้งโปรเจกต์: OCR อ่านฟอนต์ Persona 5 ไม่ออก**

P5 ใช้ฟอนต์สไตล์เฉพาะ เมนูจำนวนมากเอียง/บิด และตัวอักษรเป็นสีขาวมีขอบดำวางบน
พื้นหลังที่เปลี่ยนตลอด ถ้า OCR อ่านไม่ได้ ส่วนที่เหลือของระบบไม่มีความหมาย

**Phase 0 จึงเป็นการวัดผลล้วนๆ ไม่ใช่การสร้างฟีเจอร์** และต้องทำก่อนเขียนโค้ดอื่นทั้งหมด

### สิ่งที่เทียบ

| | RapidOCR (`rapidocr-onnxruntime`) | Windows.Media.Ocr (`winsdk`) |
|---|---|---|
| ติดตั้ง | pip อย่างเดียว | มากับ Windows (ต้องมี English language pack ซึ่งปกติมีอยู่แล้ว) |
| ความเร็วโดยประมาณ | ~150–400 ms/เฟรม (CPU) | ~10–30 ms/เฟรม |
| bounding box | ระดับบรรทัด | **ระดับคำ** (`OcrLine.words[].bounding_rect`) |
| ออฟไลน์ | ✓ | ✓ |
| ความเสี่ยง | ช้ากว่า, โมเดลเทรนกับเอกสารเป็นหลัก | ผูกกับ Windows, ต้องมี language pack |

### วิธีวัด

1. เก็บ screenshot จาก P5 จริง **20–30 ภาพ** ครอบคลุม: กล่องบทสนทนา (หลายฉาก หลายพื้นหลัง),
   เมนูหลัก, ชื่อไอเทม/สกิล, ป้ายข้อความเอียง, ตัวเลือกบทสนทนา
2. พิมพ์ ground truth ของแต่ละภาพเก็บไว้ใน `tests/fixtures/p5/*.txt`
3. รัน `scripts/
│  ├─ ocr_bakeoff.py       Phase 0: เทียบ OCR engine × preprocessing
│  └─ placeholder_probe.py หา placeholder ที่รอดจาก Google` เทียบทั้งสองเอนจิน × preprocessing 4 แบบ:
   ภาพดิบ · ขยาย 2× · ขยาย 3× + binarize (Otsu) · invert + ขยาย 2×
4. รายงาน: word accuracy, CER, latency เฉลี่ย, latency p95 ต่อชุด

### เกณฑ์ผ่าน (Exit criteria)

- **กล่องบทสนทนา: word accuracy ≥ 95%** ← บังคับ
- เมนู/ชื่อไอเทม: ≥ 80% (ถ้าไม่ผ่านเฉพาะข้อนี้ ยังไปต่อได้ แต่บันทึกว่าโหมดเมนูคุณภาพต่ำกว่า)
- latency p95 ≤ 400 ms ต่อเฟรม

**ถ้าไม่ผ่าน:** หยุด รายงานตัวเลขจริง แล้วกลับมาคุยเรื่องทางเลือก (เช่น เปลี่ยนวิธี, ลดขอบเขต,
หรือสรุปว่าแนวทางนี้ไปไม่ได้) — ไม่ใช่เดินหน้าสร้างของที่ใช้ไม่ได้จริง

เอนจินที่ชนะจะกลายเป็น default ใน `waen/ocr/` และอีกตัวยังคงอยู่เป็นตัวเลือกใน config

---

## 4. สถาปัตยกรรม

```
┌──────────────────────────────────────────────────────────┐
│ UI thread (PyQt6)                                        │
│   main_window · region_selector · overlay · tray         │
└──────────────▲───────────────────────────┬───────────────┘
               │ OverlayItem[]             │ start/stop, region, settings
               │ (signal)                  ▼
┌──────────────┴───────────────────────────────────────────┐
│ PipelineWorker (QThread)                                 │
│                                                          │
│   capture ─▶ framediff ─▶ ocr ─▶ grouping ─▶ stabilize   │
│                                                  │        │
│              layout ◀── glossary.restore ◀── translate   │
│                              ▲                   ▲        │
│                    glossary.protect ─────────────┘        │
│                                          (ThreadPoolExecutor)
└──────────────┬───────────────────────────────────────────┘
               │
┌──────────────┴───────────────────────────────────────────┐
│ platform/win32 — DPI awareness, capture-exclusion,       │
│                  global hotkeys                          │
└──────────────────────────────────────────────────────────┘
```

**กติกา thread:**
- UI ทั้งหมดอยู่บน main thread เท่านั้น
- capture / OCR / grouping / stabilize อยู่ใน `PipelineWorker` (QThread เดียว)
- การเรียก network (translate) อยู่ใน `ThreadPoolExecutor(max_workers=2)` แยกออกไป
  เพื่อไม่ให้ request ที่ช้าไปหยุดลูปจับภาพ
- ข้อมูลที่ข้าม thread เป็น **frozen dataclass เท่านั้น** ส่งผ่าน Qt signal
  ห้ามแชร์ mutable state ข้าม thread

### โครงไฟล์

```
waen/
├─ __main__.py            เข้าโปรแกรม, argparse (--cli, --debug-dump, --save-region)
├─ app.py                 ประกอบ QApplication, ต่อ signal, จัดการ lifecycle
├─ config.py              AppConfig (dataclass) + โหลด/เซฟ JSON
├─ geometry.py            Box, Region, แปลงพิกัด logical ⇄ physical
├─ models.py              TextLine, TextBlock, OverlayItem
├─ capture/
│  ├─ base.py             CaptureBackend (Protocol)
│  ├─ dxgi_backend.py     DXGI Desktop Duplication (หลัก)
│  ├─ mss_backend.py      GDI (fallback)
│  └─ factory.py          เลือก backend + fallback อัตโนมัติ
├─ ocr/
│  ├─ base.py             OcrEngine (Protocol) → TextLine[]
│  ├─ windows_ocr.py      Windows.Media.Ocr
│  ├─ rapid_ocr.py        RapidOCR
│  ├─ preprocess.py       ขยาย/binarize/invert
│  └─ factory.py
├─ pipeline/
│  ├─ worker.py           QThread ลูปหลัก
│  ├─ framediff.py        ตรวจว่าภาพเปลี่ยน
│  ├─ grouping.py         TextLine[] → TextBlock[]
│  ├─ stabilize.py        รอข้อความนิ่ง (typewriter)
│  └─ layout.py           TextBlock[] → OverlayItem[]
├─ translate/
│  ├─ base.py             Translator (Protocol)
│  ├─ google.py           deep-translator + cache + rate limit + batching
│  ├─ lookup.py           (v1.5) ค้นคลังแปลล่วงหน้า → fallback google  (หัวข้อ 16)
│  └─ glossary.py         protect/restore ศัพท์เฉพาะ
├─ platform/
│  ├─ base.py             PlatformIntegration (Protocol)
│  ├─ win32.py            ของจริง
│  └─ noop.py             สำหรับ dev บนเครื่องที่ไม่ใช่ Windows
├─ ui/
│  ├─ main_window.py      หน้าตั้งค่า
│  ├─ region_selector.py  ลากกรอบเลือกพื้นที่
│  ├─ overlay.py          วาดคำแปล
│  └─ tray.py             system tray
├─ corpus/                (v1.5) ดึงบทพูด → แปล → สร้างคลัง  (หัวข้อ 16.2)
└─ debug.py               --debug-dump
glossary/persona5.json
corpus/                   (v1.5) คลังที่ผู้ใช้สร้างเอง — .gitignore
scripts/ocr_bakeoff.py
scripts/corpus_hitrate.py (v1.5)
tests/
```

---

## 5. Data model

```python
@dataclass(frozen=True)
class Box:
    x: int; y: int; w: int; h: int      # physical screen pixels เสมอ

@dataclass(frozen=True)
class TextLine:
    text: str
    box: Box
    confidence: float

@dataclass(frozen=True)
class TextBlock:
    lines: tuple[TextLine, ...]
    source_text: str                     # ข้อความที่ต่อแล้ว พร้อมส่งแปล
    box: Box                             # bounding box รวมของทุกบรรทัด
    kind: Literal["paragraph", "standalone"]

@dataclass(frozen=True)
class OverlayItem:
    source_text: str
    translated: str
    anchor: Box                          # กล่องต้นฉบับ (ห้ามวาดทับ)
    draw: Box                            # ตำแหน่งที่จะวาดคำแปลจริง
    font_size: int
```

### พิกัด — จุดที่พังบ่อยที่สุด

**กฎเดียว: ทุก `Box` ในระบบเป็น physical screen pixel ของ virtual desktop เสมอ**
การแปลงหน่วยเกิดที่ขอบระบบเท่านั้น และรวมอยู่ใน `geometry.py` ที่เดียว:

| ขอบ | ทิศทาง | ฟังก์ชัน |
|---|---|---|
| region_selector (Qt logical) → ระบบ | × devicePixelRatio | `to_physical()` |
| OCR (พิกัดในภาพที่ครอป) → ระบบ | + region origin | `offset_by()` |
| ระบบ → overlay window (Qt logical) | ÷ devicePixelRatio | `to_logical()` |

`geometry.py` เป็นฟังก์ชันบริสุทธิ์ทั้งหมด มี unit test ครอบ scale 1.0 / 1.25 / 1.5 / 2.0
และเคสจอหลายตัวที่ origin ติดลบ (จอที่สองอยู่ทางซ้าย)

---

## 6. Pipeline

### 6.1 framediff

ลดขนาดภาพ 4 เท่าแบบ stride slice → เฉลี่ยเป็น grayscale → เทียบ mean absolute difference
กับเฟรมก่อน ถ้า > threshold (default 4.0) ถือว่าเปลี่ยน (ยกมาจาก `scan2translate` ตามเดิม)

DXGI backend มีข้อได้เปรียบ: `grab()` คืน `None` เมื่อ desktop ไม่มีเฟรมใหม่
→ ข้ามทั้ง framediff และ OCR ไปเลย ประหยัด CPU มาก แต่ยังคง framediff ไว้
เพราะ backend อาจสลับเป็น mss และเพราะเกมวาดใหม่ทุกเฟรมแม้ข้อความไม่เปลี่ยน

### 6.2 grouping — กฎจัดกลุ่ม

เรียง `TextLine` ตาม `box.y` แล้วไล่รวมทีละคู่ที่ติดกัน สองบรรทัดอยู่ **ย่อหน้าเดียวกัน**
เมื่อครบทั้งสามข้อ:

1. **ห่างแนวตั้ง** `next.box.y - (cur.box.y + cur.box.h) <= 0.8 × avg_line_height`
2. **ขอบซ้ายตรงกัน** `abs(next.box.x - cur.box.x) <= 0.15 × max(cur.box.w, next.box.w)`
3. **ทับกันแนวนอน** ช่วง x ของสองกล่องซ้อนกัน `>= 50%` ของกล่องที่แคบกว่า

- เข้าเงื่อนไข → รวมเป็น `kind="paragraph"`, `source_text` = join ด้วยช่องว่าง
  (ถ้าบรรทัดก่อนลงท้ายด้วย `-` ให้ตัด `-` แล้วต่อกันโดยไม่เว้นวรรค)
- ไม่เข้า → แต่ละบรรทัดเป็น `kind="standalone"` ของตัวเอง

ค่าคงที่ทั้งสามอยู่ใน config ปรับได้ (`grouping.vertical_gap_ratio`,
`grouping.left_align_tolerance`, `grouping.horizontal_overlap_min`)

**เป็นฟังก์ชันบริสุทธิ์** — เทสด้วย `TextLine` ที่สร้างเองได้ทั้งหมด ไม่ต้องมีภาพ ไม่ต้องมีจอ

### 6.3 stabilize — รับมือ typewriter effect

P5 ไล่ตัวอักษรทีละตัว ถ้าแปลทันทีจะได้ `"Welco"` → `"Welcome to th"` → `"Welcome to this vil"`
รัวๆ เปลืองทั้ง request ทั้งสายตา

จับคู่บล็อกข้ามเฟรมด้วยตำแหน่ง (IoU ของ box ≥ 0.5 ถือว่าเป็นบล็อกเดิม) แล้วบล็อกจะ
"นิ่ง" ก็ต่อเมื่อครบทุกข้อ:

1. ข้อความเหมือนเฟรมก่อนติดกัน `>= stable_frames` ครั้ง (default 2)
2. **ไม่อยู่ในสภาพกำลังพิมพ์** — ถ้าข้อความปัจจุบันขึ้นต้นเหมือนข้อความก่อนหน้าแต่ยาวกว่า
   (`new.startswith(prev) and len(new) > len(prev)`) แปลว่ายังพิมพ์อยู่ → รีเซ็ตตัวนับ
3. ผ่านไปแล้ว `>= min_stable_ms` (default 250 ms) นับจากครั้งแรกที่เห็นข้อความนี้
4. ข้อความยาวพอ — หลังตัดช่องว่างแล้วต้อง `>= 2` ตัวอักษร

**เป็นฟังก์ชันบริสุทธิ์** (รับเวลาเป็นพารามิเตอร์ ไม่เรียก `time.time()` เอง) → เทสได้เต็ม

### 6.4 layout — วางคำแปลไม่ให้ทับกันเองและไม่ทับต้นฉบับ

เรียงบล็อกจากบนลงล่าง แล้วจองพื้นที่ทีละอันแบบ greedy เก็บ list ของ rect ที่จองแล้ว
สำหรับแต่ละบล็อก ไล่ตามลำดับจนกว่าจะได้ที่:

1. วาง **เหนือ** anchor ห่าง `gap` (default 4 px)
2. ถ้าล้นขอบบนของจอ หรือชนของที่จองไว้ → วาง **ใต้** anchor
3. ยังชน → ลดขนาดฟอนต์ทีละ 1 pt (ต่ำสุด 11 pt) แล้วลองข้อ 1–2 ใหม่
4. ยังชน → วาง **ทับ** anchor ด้วยพื้นหลังทึบ 85% (ทางเลือกสุดท้าย)
   ผู้ใช้กด `Ctrl+Alt+H` เพื่อสลับซ่อน/แสดงคำแปลทั้งหมดและดูต้นฉบับได้

**เป็นฟังก์ชันบริสุทธิ์** — รับ `TextBlock[]` + ขนาดจอ + ฟังก์ชันวัดความกว้างข้อความ
คืน `OverlayItem[]` ฟังก์ชันวัดข้อความถูกฉีดเข้ามา (dependency injection) เพื่อให้เทส
ใช้ตัววัดปลอมที่คำนวณตรงไปตรงมาได้ ไม่ต้องมี Qt

---

## 7. การแปล

### 7.1 backend

`translate/base.py` นิยาม Protocol เดียว:

```python
class Translator(Protocol):
    def translate_many(self, texts: list[str]) -> list[str | None]: ...
```

v1 มี implementation เดียว: `GoogleTranslator` (ผ่าน `deep-translator`, endpoint ฟรี ไม่ต้องมี key)
v1.5 เพิ่ม `LookupTranslator` ที่ห่อ `GoogleTranslator` ไว้เป็น fallback (หัวข้อ 16.4)
`None` = แปลไม่สำเร็จ ผู้เรียกต้องแสดงสถานะและไม่ล้ม

### 7.2 cache, rate limit, batching

Google endpoint ฟรีมีการจำกัดอัตรา และเราจะยิงบ่อยมาก จึงต้องมีทั้งสามชั้น:

- **LRU cache** 1000 รายการ key = `(source, target, text)` — บทสนทนาที่อ่านซ้ำ/ย้อนกลับมา
  จะไม่แตะเน็ตเลย
- **Rate limit** ไม่เกิน 5 request/วินาที (token bucket) และ backoff แบบทวีคูณ
  1.5s → 3s → 6s เมื่อเจอ error สูงสุด 3 ครั้ง แล้วรายงานสถานะขึ้น UI
- **Batching** เมื่อมีบล็อก `standalone` หลายอันในเฟรมเดียว ให้ต่อด้วย `\n` ส่งไปครั้งเดียว
  แล้วแยกผลลัพธ์ด้วย `\n`
  **ถ้าจำนวนบรรทัดที่ได้กลับมาไม่ตรงกับที่ส่งไป ให้ทิ้งผลนั้นแล้วยิงทีละอันแทน**
  (เงื่อนไขนี้ต้องมีเทสคุม เพราะ Google ไม่รับประกันว่าจะรักษาจำนวนบรรทัด)

### 7.3 glossary — ทำให้ Google ใช้ได้กับ P5

`glossary/persona5.json` มีสองส่วน:

```json
{
  "keep": ["Ryuji", "Ann", "Makoto", "Futaba", "Yusuke", "Haru", "Morgana",
           "Joker", "Mementos", "Kamoshida", "Sae", "Akechi"],
  "map": {
    "Palace": "พาเลซ",
    "Persona": "เพอร์โซนา",
    "Velvet Room": "ห้องกำมะหยี่",
    "Confidant": "ผู้ร่วมอุดมการณ์",
    "Phantom Thieves": "จอมโจรพันหน้า",
    "Treasure": "สมบัติ",
    "Shadow": "เงา"
  }
}
```

- `keep` = คำที่ต้องออกมาเป็นภาษาอังกฤษเหมือนเดิม (ชื่อคน ชื่อสถานที่)
- `map` = คำที่ต้องแปลเป็นคำไทยที่กำหนดตายตัว

**วิธีทำงาน (protect → translate → restore):**

1. ก่อนส่งแปล แทนคำที่ตรงกับ glossary ด้วย placeholder ที่มีหมายเลขกำกับ
2. ส่งข้อความที่ถูก protect แล้วไปแปล
3. หลังแปล แทน placeholder กลับด้วยคำต้นฉบับ (`keep`) หรือคำไทยที่กำหนด (`map`)
4. **ถ้า placeholder หายไปจากผลลัพธ์** (Google กลืนหรือแปลงมันไป) ให้ถอยไปใช้
   วิธีสำรอง: แปลข้อความดิบตามปกติ แล้วค่อยแทนคำผิดที่รู้จักด้วยคำที่ถูก

**เรื่องที่ยังไม่รู้และต้องวัดจริง:** placeholder รูปแบบไหนที่ Google ส่งกลับมาครบ
`scripts/placeholder_probe.py` จะทดสอบผู้สมัคร 5 แบบ (`⟦0⟧`, `[[0]]`, `{0}`, `@@0@@`, `#0#`)
กับประโยคตัวอย่าง 20 ประโยค แล้วเลือกตัวที่รอด 100% มาเป็นค่าเริ่มต้นใน config
ส่วนกลไก fallback ในข้อ 4 มีอยู่เสมอไม่ว่าผลจะออกมาอย่างไร

การจับคู่คำใช้ word boundary และไล่จากวลียาวไปสั้น (`Velvet Room` ก่อน `Room`)
`glossary.py` เป็นฟังก์ชันบริสุทธิ์ เทสได้ครบด้วย translator ปลอม

---

## 8. Overlay และการกันจับภาพตัวเอง

### 8.1 คุณสมบัติหน้าต่าง overlay

- `FramelessWindowHint | WindowStaysOnTopHint | Tool | WindowTransparentForInput`
- `WA_TranslucentBackground`, `WA_TransparentForMouseEvents`, `WA_ShowWithoutActivating`
- ย้ำด้วย ctypes บน Windows: ใส่ `WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE`
  ผ่าน `SetWindowLongPtrW` เพื่อให้คลิกทะลุแน่นอนและไม่แย่ง focus จากเกม
- ครอบเต็ม virtual desktop หนึ่งบาน วาดทุก `OverlayItem` ในบานเดียว
  (ง่ายกว่าและกะพริบน้อยกว่าการสร้างหน้าต่างต่อกล่อง)
- ฟอนต์ไทย: `Leelawadee UI` → fallback `Tahoma` → ฟอนต์ระบบ
  (Leelawadee UI มากับ Windows 8 ขึ้นไป และเรนเดอร์สระ/วรรณยุกต์ไทยถูกต้อง)
- แต่ละ item วาดพื้นหลังโค้งมนทึบ ~80% + ข้อความสีขาว เพื่อให้อ่านออกบนพื้นหลังเกมทุกสี

### 8.2 กันจับภาพตัวเอง — สามชั้น

1. **`SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)`** — overlay หายไปจากภาพที่จับ
   ทั้ง GDI และ DXGI ต้องการ Windows 10 build 19041 (2004) ขึ้นไป
   ตรวจค่าที่คืนมา ถ้าล้มเหลวให้ log แล้วเปิดชั้นถัดไป
2. **Mask** — ก่อนส่งภาพเข้า OCR ให้ทาสีดำทับพื้นที่ที่ overlay กำลังวาดอยู่
   (worker รู้ `OverlayItem[]` ล่าสุดอยู่แล้ว) ดีกว่าวิธีซ่อน-จับ-โชว์ของเดิมที่ทำให้จอกะพริบ
3. **ตัวกรองอักษรไทย** — ต้นทางเป็นภาษาอังกฤษเสมอ ดังนั้น `TextLine` ใดที่มีอักษรไทย
   (ช่วง Unicode U+0E00–U+0E7F) เกิน 30% ของตัวอักษรทั้งหมด ให้ทิ้งทันที ชั้นนี้ราคาถูกมากและกันได้เด็ดขาดแม้สองชั้นแรกพลาด

---

## 9. การจับภาพ และข้อจำกัดเรื่อง fullscreen

### 9.1 ลำดับการเลือก backend

1. **DXGI Desktop Duplication** (`bettercam`, ถ้าไม่ได้ลอง `dxcam`) — เร็ว, ทำงานกับ
   borderless และเกมที่ Windows แปลงเป็น flip-model, คืน `None` เมื่อไม่มีเฟรมใหม่
2. **mss (GDI)** — fallback เมื่อ DXGI ใช้ไม่ได้ (ไดรเวอร์บางตัว, บาง setup หลาย GPU)

เลือกอัตโนมัติตอนเปิดโปรแกรมโดยลองจับจริงหนึ่งเฟรมแล้วเช็คว่าไม่ใช่ภาพดำล้วน
ผู้ใช้บังคับเลือกเองได้ใน config

### 9.2 ข้อจำกัดที่ต้องพูดตรงๆ

ถ้าเกมอยู่ใน **exclusive fullscreen จริง** หน้าต่างธรรมดาวาดทับไม่ได้เลย ไม่ว่าโปรแกรมใด
การจะทำได้ต้อง hook DirectX/Vulkan present chain แบบที่ Steam / Discord / RTSS overlay ทำ
ซึ่งเสี่ยงต่อ anti-cheat และเป็นงานคนละขนาดกับโปรเจกต์นี้ — **อยู่นอกขอบเขต**

**ทางที่ใช้ได้จริง: ตั้งเกมเป็น Borderless windowed** ซึ่งเต็มจอเหมือนกันทุกประการ
นอกจากนี้ Windows 10/11 มี fullscreen optimizations ที่แปลง DX11/DX12 fullscreen เป็น
flip-model ให้เองในเกมส่วนใหญ่ ทำให้ overlay ทำงานได้อยู่ดี

Phase 1 ต้องยืนยันกับ P5R ตัวจริงว่าโหมดไหนใช้ได้บ้าง แล้วบันทึกผลลง README

---

## 10. UI และการควบคุม

**หน้าต่างตั้งค่า** (เล็ก เปิดจาก tray): ปุ่มเลือกพื้นที่ · เริ่ม/หยุด · ขนาดฟอนต์ ·
ความทึบพื้นหลัง · เลือกไฟล์ glossary · เลือก OCR engine และ capture backend ·
แถบสถานะแสดง fps, latency แต่ละขั้น, ค่า confidence เฉลี่ย, จำนวน request ที่ค้าง

**System tray**: เริ่ม/หยุด, เลือกพื้นที่ใหม่, เปิดหน้าตั้งค่า, ออก

**Hotkey ทั้งระบบ** (`RegisterHotKey`, ทำงานแม้โฟกัสอยู่ที่เกม):

| ปุ่ม | ทำอะไร |
|---|---|
| `Ctrl+Alt+T` | เริ่ม/หยุดการเฝ้าดู |
| `Ctrl+Alt+R` | เลือกพื้นที่ใหม่ |
| `Ctrl+Alt+H` | สลับซ่อน/แสดงคำแปล (กดสลับ ไม่ใช่กดค้าง — `RegisterHotKey` ส่งเฉพาะจังหวะกดลง ไม่มีสัญญาณตอนปล่อย จึงทำแบบกดค้างไม่ได้) |

**พื้นที่ที่เฝ้า:** หนึ่งกรอบ ผู้ใช้ลากได้อิสระ จะเลือกเฉพาะกล่องบทสนทนาด้านล่าง
หรือคลุมทั้งจอเพื่อให้จับเมนูด้วยก็ได้ — เพราะ grouping จัดการข้อความหลายก้อน
ในกรอบเดียวอยู่แล้ว การรองรับหลายกรอบพร้อมกันจึงไม่จำเป็นใน v1
(กรอบใหญ่ขึ้น = OCR ช้าลง แถบสถานะจะบอกให้เห็น)

---

## 11. Config

เก็บที่ `%APPDATA%\waen\config.json` มี `version` สำหรับ migrate ในอนาคต

```jsonc
{
  "version": 1,
  "region": null,                      // null = ยังไม่ได้เลือกพื้นที่
  "region_scale": 1.0,
  "source_lang": "en",
  "target_lang": "th",
  "ocr_engine": "auto",          // auto | windows | rapid
  "capture_backend": "auto",     // auto | dxgi | mss
  "poll_interval_ms": 250,
  "diff_threshold": 4.0,
  "stable_frames": 2,
  "min_stable_ms": 250,
  "grouping": {
    "vertical_gap_ratio": 0.8,
    "left_align_tolerance": 0.15,
    "horizontal_overlap_min": 0.5
  },
  "overlay": {
    "font_family": "Leelawadee UI",
    "font_size": 16,
    "min_font_size": 11,
    "background_opacity": 0.8,
    "gap_px": 4
  },
  "glossary_path": "glossary/persona5.json",
  "corpus_path": null,                 // (v1.5) null = ไม่ใช้คลัง, ใช้ Google ตรง
  "corpus_threshold": 85,              // (v1.5) คะแนน fuzz.ratio ขั้นต่ำที่ถือว่า hit
  "placeholder_template": "[[{i}]]",   // ค่าเริ่มต้นชั่วคราว placeholder_probe.py เป็นผู้ตัดสิน
  "hotkeys": {
    "toggle": "ctrl+alt+t",
    "select_region": "ctrl+alt+r",
    "hide": "ctrl+alt+h"
  }
}
```

ค่าที่หายหรือผิดชนิดให้ถอยไปใช้ค่าเริ่มต้นแทน ไม่ล้มทั้งโปรแกรม

---

## 12. การจัดการข้อผิดพลาด

| เหตุการณ์ | พฤติกรรม |
|---|---|
| จับภาพล้มเหลว | log, แสดงสถานะ, ลอง backend สำรอง 1 ครั้ง, ถ้ายังไม่ได้ให้หยุดและบอกผู้ใช้ |
| OCR โยน exception | ข้ามเฟรมนั้น เพิ่มตัวนับ, ถ้าพลาดติดกัน 10 ครั้งให้หยุดและรายงาน |
| แปลล้มเหลว | คืน `None`, ไม่วาด item นั้น, แสดง "แปลไม่สำเร็จ" บนแถบสถานะ, ลูปเดินต่อ |
| ถูก rate limit | backoff ทวีคูณ, แสดงสถานะ, ไม่ล้ม |
| `WDA_EXCLUDEFROMCAPTURE` ใช้ไม่ได้ | log แล้วเปิดโหมด mask อัตโนมัติ แจ้งผู้ใช้ครั้งเดียว |
| ไม่มี glossary ตาม path | ทำงานต่อโดยไม่มี glossary + เตือนหนึ่งครั้ง |
| ไม่มี/เปิดคลังไม่ได้ (v1.5) | ใช้ `GoogleTranslator` ตรง + เตือนหนึ่งครั้ง |

หลักการ: **ไม่มีอะไรทำให้โปรแกรมตายกลางเกม** ทุกความล้มเหลวลดระดับลงอย่างนุ่มนวลและมองเห็นได้

---

## 13. การทดสอบ

| ชั้น | ทดสอบอย่างไร | ต้องมีจอ/เกมไหม |
|---|---|---|
| `geometry` | unit test ทุก scale + จอหลายตัว origin ติดลบ | ไม่ |
| `grouping` | unit test ด้วย `TextLine` ที่สร้างเอง: ย่อหน้าธรรมดา, ย่อหน้าเว้นบรรทัด, เมนูแนวนอน, คำเดี่ยว, คำที่ตัดด้วย hyphen | ไม่ |
| `stabilize` | unit test จำลอง typewriter ทีละตัวอักษร, ข้อความสลับไปมา, บล็อกขยับตำแหน่ง | ไม่ |
| `glossary` | unit test ด้วย translator ปลอม รวมเคส placeholder หาย → ต้องถอยไปวิธีสำรอง | ไม่ |
| `layout` | unit test ด้วยตัววัดข้อความปลอม: ชนขอบบน, ชนกันเอง, ต้องย่อฟอนต์, ต้องวางทับ | ไม่ |
| `translate` | unit test cache/rate limit/batching ด้วย backend ปลอม + เคสจำนวนบรรทัดไม่ตรง | ไม่ |
| `corpus/normalize` (v1.5) | unit test: quote/dash หลายแบบ, หลายบรรทัด, ช่องว่างซ้ำ — ผลต้องเท่ากันทั้งฝั่ง build และ runtime | ไม่ |
| `corpus/extract` (v1.5) | unit test ด้วย fixture สังเคราะห์ (ไม่ใช้ข้อความจากเกม): `page_break` ตัดถูก, `variable` แทนถูก, `strip` ทิ้งถูก, `id` คงที่ข้ามการรัน | ไม่ |
| `translate/lookup` (v1.5) | unit test ด้วยคลังเล็กใน memory: hit ตรงตัว, hit ที่ OCR เพี้ยน, คะแนนก้ำกึ่ง threshold, miss → fallback ถูกเรียก | ไม่ |
| hit rate (v1.5) | `scripts/corpus_hitrate.py` บน `--debug-dump` จากการเล่นจริง | ต้องมี dump |
| `ocr` | golden test กับ screenshot P5 จริงใน `tests/fixtures/p5/` เทียบกับ ground truth | ต้องมีภาพ (ไม่ต้องมีเกมรัน) |
| `capture` / `overlay` | ทดสอบมือบน Windows ตาม checklist ของแต่ละ phase | ต้องมี |
| ทั้งระบบ | รันจริงกับ P5 พร้อม `--debug-dump` | ต้องมี |

### `--debug-dump DIR`

ทุกรอบที่มีการแปลจะเขียนลงโฟลเดอร์:
- `NNNN_frame.png` — ภาพดิบที่จับได้
- `NNNN_boxes.png` — ภาพเดิมวาดกรอบทับ (สีตาม `kind`)
- `NNNN.json` — `TextLine[]`, `TextBlock[]`, ข้อความก่อน/หลัง glossary, ผลแปล, เวลาที่ใช้แต่ละขั้น
  (v1.5 เพิ่ม `corpus_hit`, `corpus_score`, `corpus_entry_id` ต่อบล็อก)

เก็บสูงสุด 500 รอบแล้ววนทับ **จำเป็นมาก** เพราะทำให้ผู้ช่วยเขียนโค้ดวินิจฉัยได้เองว่า
พังที่ขั้นไหน โดยผู้ใช้ไม่ต้องมานั่งอธิบายอาการ

---

## 14. ลำดับการสร้าง

| Phase | ขอบเขต | จบเมื่อ (ตรวจได้จริง) |
|---|---|---|
| **0. พิสูจน์ OCR** | เก็บ screenshot P5 + ground truth + `scripts/ocr_bakeoff.py` | รายงานตัวเลขออกมา และผ่านเกณฑ์หัวข้อ 3 — **ไม่ผ่าน = หยุด กลับมาคุยใหม่** |
| **1. จับภาพ + พิกัด** | `geometry`, `capture/*`, `region_selector`, DPI awareness | ลากกรอบทับกล่องบทสนทนา P5 แล้ว `--save-region out.png` ได้ภาพตรงพิกเซล ทดสอบที่ scale 100% และ 150% |
| **2. อ่าน → จัดกลุ่ม → แปล (CLI)** | `ocr/*`, `grouping`, `stabilize`, `translate/*`, `glossary` | `python -m waen --cli` แล้วเดินคุยกับ NPC ใน P5 เห็นคำแปลไหลออก terminal บรรทัดต่อบรรทัด ไม่แปลกลางคำ |
| **3. Overlay** | `layout`, `ui/overlay`, กันจับภาพตัวเองสามชั้น | คำแปลลอยเหนือกล่องบทสนทนาจริงในเกม ต้นฉบับไม่ถูกบัง ไม่มีคำแปลซ้อนกัน ไม่วนแปลตัวเอง |
| **4. จูนกับเกมจริง** | ปรับค่า grouping/stabilize, เติม glossary, แก้เคสที่เจอ | เล่น P5 ต่อเนื่อง 30 นาที: ไม่มีคำแปลค้าง ไม่มีแปลกลางคำ CPU และ memory คงที่ |
| **5. ใช้งานจริง** | hotkey, tray, หน้าตั้งค่า, PyInstaller | `.exe` เปิดบนเครื่อง Windows ที่ไม่มี Python แล้วใช้งานครบทุกฟีเจอร์ |
| **6. คลังแปลล่วงหน้า (v1.5)** | `corpus/*`, `translate/lookup`, `corpus_hitrate` — แบ่ง 6a/6b/6c ตามหัวข้อ 16.5 | 6b: hit rate ≥ 90% โดยยังไม่เสียเงิน → 6c: สลับคลังที่แปลแบบมี context |

Phase 0 **ต้องทำบนเครื่อง Windows** เพราะต้องเทียบ Windows.Media.Ocr และต้องใช้ภาพจากเกมจริง

---

## 15. เรื่องที่รู้ว่ายังไม่รู้

รายการนี้ตั้งใจให้อยู่ในเอกสาร เพราะเป็นสิ่งที่จะรู้คำตอบตอนลงมือเท่านั้น:

1. **OCR อ่านฟอนต์ P5 ได้ไหม** — Phase 0 ตอบ มีเกณฑ์และมีทางออกถ้าไม่ผ่านแล้ว
2. **placeholder แบบไหนรอดจาก Google** — `scripts/placeholder_probe.py` ตอบ และมี fallback อยู่แล้ว
3. **P5R PC มีโหมด Borderless หรือไม่ และ fullscreen จับภาพได้ไหม** — Phase 1 ตอบ
4. **`bettercam`/`dxcam` ติดตั้งและทำงานบนเครื่องเป้าหมายได้ไหม** — Phase 1 ตอบ มี mss เป็น fallback
5. **latency รวมยอมรับได้ไหมตอนเล่นจริง** — Phase 4 ตอบ ถ้าช้าไปมีทางลด: ลดพื้นที่กรอบ,
   ลด poll interval, ใช้ Windows OCR, ข้ามการแปลเมื่อ cache hit
6. **(v1.5) มี script dump ภาษาอังกฤษของ P5R ให้ใช้เลยไหม** — ถ้ามี ข้าม CPK/AtlusScriptTools
   ไปใช้ `plaintext` adapter ได้ทันที; Phase 6a ตอบ
7. **(v1.5) ข้อความบนจอตรงกับไฟล์แค่ไหน** — tag `page_break` ของ P5R ตัดตรงกับหน้าจอจริงไหม,
   OCR เพี้ยนแค่ไหน → `threshold` ควรเป็นเท่าไหร่; Phase 6b ตอบด้วย hit rate
8. **(v1.5) คลังใหญ่แค่ไหน จ่ายเท่าไหร่** — `--dry-run` นับตัวอักษรก่อน แล้วค่อยเลือก backend;
   Phase 6a ตอบ

---

## 16. คลังแปลล่วงหน้า (Pre-translated corpus) — v1.5

> เพิ่ม 2026-09-11 · ไม่บล็อก v1 · ทำหลัง Phase 4 ผ่านแล้ว

### 16.1 แนวคิด

Google ฟรีแปลทีละบรรทัดโดยไม่รู้ว่าใครพูดกับใคร ผลคือสรรพนามและระดับภาษาไทย
(ผม/ฉัน/ข้า, ครับ/ค่ะ) มั่ว แก้ที่ runtime ไม่ได้เพราะไม่มี context ให้

ทางออก: **ดึงบทพูดทั้งเกมออกมาจากไฟล์เกม แปลรอบเดียวแบบมี context ด้วยบริการที่ดีกว่า
(จ่ายครั้งเดียว) เก็บเป็นคลังในเครื่อง** ตอนเล่น OCR ได้ข้อความอะไรก็ไปค้นคลังก่อน
เจอ → ใช้คำแปลจากคลัง ไม่เจอ → ถอยไป Google ตามเดิม

```
[offline — ทำครั้งเดียวต่อเกม]
 ไฟล์เกม ─▶ extract (GameAdapter) ─▶ ScriptEntry[] ─▶ segment/normalize
          ─▶ translate แบบมี context ─▶ corpus/<game>.sqlite

[runtime — ตอนเล่น]
 OCR text ─▶ normalize ─▶ LookupTranslator ─┬─ hit  ─▶ คำแปลจากคลัง (ไม่แตะเน็ต)
                                             └─ miss ─▶ GoogleTranslator (เดิม)
```

สิ่งที่ได้นอกจากคุณภาพ:

- **latency เป็นศูนย์** เมื่อ hit — ไม่มี network, ไม่โดน rate limit
- **ทน OCR ผิดได้** — fuzzy match จับ `"Phantorn Thleves"` เข้ากับ `"Phantom Thieves"` ได้
  แล้วแสดงคำแปลที่ถูก เท่ากับคลังช่วย "แก้" OCR ให้ ลดแรงกดดันจากความเสี่ยงข้อ 3
- **ยังไม่ต้องลง mod** — อ่านไฟล์เกมอย่างเดียว ไม่แก้ ไม่ hook จึงใช้กับ Steam/Game Pass
  ได้ทุก build และไม่ยุ่งกับ anti-cheat

**ลิขสิทธิ์:** บทพูดเป็นของผู้พัฒนาเกม คลังที่ดึงและแปลแล้ว (`corpus/*.sqlite`, `*.jsonl`)
เป็นไฟล์ที่ผู้ใช้สร้างเองในเครื่อง **อยู่ใน `.gitignore` ห้าม commit** สิ่งที่อยู่ใน repo
คือเครื่องมือดึงและ adapter เท่านั้น

### 16.2 ระบบดึงบทพูด — ออกแบบให้ใช้กับเกมอื่นได้

แยกเป็น 3 ชั้นที่ไม่รู้จักกัน เพื่อให้เกมใหม่เขียนเฉพาะส่วนที่ต่างจริงๆ:

```
waen/corpus/
├─ models.py              ScriptEntry
├─ normalize.py           normalize() — ใช้ร่วมกันทั้ง build และ runtime (ห้ามมีสองสำเนา)
├─ archives/              ชั้น 1: แกะไฟล์บรรจุ
│  ├─ base.py             ArchiveReader (Protocol): list() / read(name) -> bytes
│  ├─ plain_dir.py        โฟลเดอร์ธรรมดา
│  └─ cpk.py              CRI CPK (P5R, เกม Atlus/Sega อื่นๆ)
├─ formats/               ชั้น 2: ถอดรหัสไฟล์ข้อความ
│  ├─ base.py             TextFormat (Protocol): decode(bytes, name) -> Iterator[RawMessage]
│  ├─ plaintext.py        .txt / .csv / .json / .jsonl — ตัวหารร่วมน้อยที่สุด
│  └─ atlus_msg.py        .msg ที่ได้จาก AtlusScriptTools (decompile .bmd)
├─ adapters/              ชั้น 3: ความรู้เฉพาะเกม
│  ├─ base.py             GameAdapter (Protocol) + TagRules
│  ├─ plaintext.py        เกมใดก็ได้ที่มี script dump อยู่แล้ว
│  └─ persona5r.py        P5R PC
├─ extract.py             ต่อ archive → format → adapter → ScriptEntry[] → .src.jsonl
├─ translate.py           .src.jsonl → .th.jsonl (มี checkpoint, --dry-run บอกจำนวนตัวอักษร)
├─ build.py               .th.jsonl → .sqlite (FTS5 trigram)
└─ __main__.py            python -m waen.corpus extract|translate|build|stats
```

**Data model:**

```python
@dataclass(frozen=True)
class ScriptEntry:
    id: str                    # "<game>:<file>:<msg>:<page>" — คงที่ข้ามการรัน
    game: str
    scene: str                 # กุญแจจัดกลุ่มเพื่อส่งแปลพร้อมกัน (ปกติ = ไฟล์ .msg)
    order: int                 # ลำดับใน scene
    speaker: str | None
    text_raw: str              # ตามไฟล์ ยังมี tag
    text: str                  # ถอด tag แล้ว แทนตัวแปรแล้ว = สิ่งที่จะปรากฏบนจอ
```

**`GameAdapter` — สิ่งเดียวที่ต้องเขียนใหม่ต่อเกม:**

```python
class GameAdapter(Protocol):
    id: str                                        # "persona5r"
    def detect(self, game_dir: Path) -> bool: ...  # มีไฟล์ที่คาดหวังไหม
    def sources(self, game_dir: Path) -> Iterator[tuple[ArchiveReader, TextFormat, str]]: ...
    tag_rules: TagRules
```

`TagRules` บอก extractor ว่าจะทำอะไรกับ tag ในข้อความ มี 3 ประเภทเท่านั้น:

| ประเภท | ความหมาย | ตัวอย่าง P5R |
|---|---|---|
| `page_break` | ตัดเป็น entry ใหม่ — **หนึ่ง entry = หนึ่งหน้าจอ** เพราะ OCR เห็นทีละหน้า | `[w]` |
| `variable` | แทนด้วยค่าจาก CLI (`--var name="Ren Amamiya"`) | tag ชื่อตัวเอก |
| `strip` | ทิ้ง (สี, ความเร็วพิมพ์, เสียง) | ที่เหลือทั้งหมด |

ถ้าไม่ตัดตาม `page_break` การ match จะพังทั้งระบบ เพราะข้อความในไฟล์ยาวกว่าที่เห็นบนจอ
นี่คือกฎข้อเดียวที่สำคัญที่สุดของ extractor

**P5R adapter:** CPK → `.bmd` → decompile ด้วย AtlusScriptTools (`AtlusScriptCompiler.exe`,
.NET, เรียกผ่าน subprocess, ผู้ใช้ติดตั้งเองและระบุ path) → `.msg` → `atlus_msg` format
**ทางลัดที่ต้องลองก่อน:** ถ้ามี script dump ภาษาอังกฤษของ P5R อยู่แล้วบน GitHub/wiki
ใช้ `plaintext` adapter อ่านได้ทันที ไม่ต้องแตะ CPK เลย

**เกมถัดไป** เขียน adapter ใหม่ไฟล์เดียว (+ format/archive ถ้าเป็นชนิดที่ยังไม่มี)
ส่วน `normalize`, `translate`, `build`, `LookupTranslator` ใช้ของเดิมทั้งหมด

### 16.3 แปลคลัง

`python -m waen.corpus translate --in p5r.src.jsonl --backend google|<paid> --out p5r.th.jsonl`

- จัดกลุ่มตาม `scene` ส่งเป็นหน้าต่างละ N entry **พร้อมชื่อผู้พูด** เพื่อให้ผู้แปลเห็น context
  → interface ต่างจาก runtime: `CorpusTranslator.translate_scene(entries) -> list[str]`
- backend `google` = ทีละบรรทัดผ่าน `GoogleTranslator` เดิม **ฟรี ใช้ทดสอบระบบ match
  ก่อนจ่ายเงิน**
- backend เสียเงิน/LLM = ส่งทั้ง scene + glossary เป็นคำสั่ง (ไม่ต้องใช้ placeholder)
  เลือกเจ้าตอนรู้ขนาดคลังจาก `--dry-run` แล้ว
- **resumable**: checkpoint ต่อ scene รันซ้ำข้ามที่ทำแล้ว เพราะการแปลหลักแสนบรรทัดจะ
  ถูกขัดจังหวะแน่นอน
- ตรวจจำนวนบรรทัดกลับต้องเท่าที่ส่ง (กฎเดียวกับ 7.2) ไม่เท่า → แปล scene นั้นทีละ entry

### 16.4 `LookupTranslator` — ฝั่ง runtime

`translate/lookup.py` implement `Translator` Protocol เดิม → เสียบแทน `GoogleTranslator`
ได้โดย pipeline ไม่รู้ตัว

```python
class LookupTranslator:
    def __init__(self, corpus_path: Path, fallback: Translator, threshold: int = 85): ...
    def translate_many(self, texts: list[str]) -> list[str | None]: ...
```

ขั้นตอนต่อข้อความ:

1. `normalize(text)` — ฟังก์ชันเดียวกับตอน build (lowercase, รวมบรรทัด, unify quote/dash,
   ตัดเครื่องหมายวรรคตอน, ยุบช่องว่าง)
2. ดึงผู้สมัคร top-20 จาก SQLite **FTS5 trigram** (มีใน sqlite ที่มากับ Python 3.11 บน
   Windows แล้ว ไม่ต้องสร้าง index เอง)
3. ให้คะแนนด้วย `rapidfuzz.fuzz.ratio` กับ `text` ที่ normalize แล้ว
4. คะแนนสูงสุด `>= threshold` → คืนคำแปลจากคลัง **ข้าม glossary** (คลังสอดคล้องอยู่แล้ว)
5. ไม่ถึง → ส่ง `fallback.translate_many([text])` ผ่าน glossary ตามเส้นทางเดิม

เส้นทาง hit ไม่แตะเน็ต จึงเรียกจาก `PipelineWorker` ได้โดยตรง แต่เพื่อไม่ให้มีสองเส้นทาง
ให้ทั้ง hit และ miss ผ่าน `ThreadPoolExecutor` เดิมเหมือนกัน (hit จะกลับมาในหลัก ms)

**การวัดผล:** `--debug-dump` เพิ่ม `corpus_hit`, `corpus_score`, `corpus_entry_id` ต่อบล็อก
และ `scripts/corpus_hitrate.py` อ่าน dump ทั้งโฟลเดอร์แล้วรายงาน hit rate — ตัวเลขนี้คือ
เกณฑ์ผ่านของ Phase 6

### 16.5 ลำดับทำ — แยกความเสี่ยงออกจากเงิน

| ขั้น | ทำอะไร | จบเมื่อ | เสียเงิน |
|---|---|---|---|
| 6a | `corpus/` extract + `plaintext` + `persona5r` adapter | `stats` รายงานจำนวน entry/ตัวอักษร → รู้ราคา | ไม่ |
| 6b | แปลคลังด้วย `google` + `LookupTranslator` + hitrate script | เล่น P5 30 นาที hit rate บนกล่องบทสนทนา **≥ 90%** | ไม่ |
| 6c | แปลคลังใหม่ด้วย backend เสียเงินแบบมี context | สลับไฟล์คลัง โค้ดไม่เปลี่ยน คำแปลอ่านแล้วสรรพนามถูก | ครั้งเดียว |

ถ้า 6b ไม่ถึงเกณฑ์ (OCR เพี้ยนเกิน หรือข้อความบนจอต่างจากไฟล์มากกว่าที่คิด) หยุดก่อน 6c
ยังไม่เสียเงิน และ v1 ยังใช้งานได้เต็มเหมือนเดิม
