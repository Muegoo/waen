"""Phase 0: เทียบ OCR engine x preprocessing บนภาพจริงจาก Persona 5

รัน:
    python -m scripts.ocr_bakeoff
    python -m scripts.ocr_bakeoff --fixtures tests/fixtures/p5 --out docs/phase0-ocr-report.md

ผลลัพธ์ของสคริปต์นี้เป็นตัวตัดสินว่าโปรเจกต์เดินต่อหรือหยุด อ่านเกณฑ์ที่
docs/superpowers/specs/2026-09-10-waen-design.md หัวข้อ 3
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from waen.metrics import character_error_rate, word_accuracy
from waen.ocr.preprocess import PIPELINES, scale_factor_of

DEFAULT_FIXTURES = Path("tests/fixtures/p5")
DEFAULT_REPORT = Path("docs/phase0-ocr-report.md")

DIALOGUE_ACCURACY_GATE = 0.95
MENU_ACCURACY_TARGET = 0.80
LATENCY_P95_GATE_MS = 400.0


@dataclass(frozen=True)
class Case:
    name: str
    group: str
    image_path: Path
    truth: str


@dataclass(frozen=True)
class CaseResult:
    engine: str
    pipeline: str
    name: str
    group: str
    word_accuracy: float
    cer: float
    elapsed_ms: float
    text: str


@dataclass(frozen=True)
class Summary:
    engine: str
    pipeline: str
    group: str
    mean_word_accuracy: float
    mean_cer: float
    p95_ms: float
    count: int


def load_cases(directory: Path) -> list[Case]:
    cases: list[Case] = []
    for image_path in sorted(directory.glob("*.png")):
        truth_path = image_path.with_suffix(".txt")
        if not truth_path.exists():
            continue
        cases.append(
            Case(
                name=image_path.stem,
                group=image_path.stem.split("_")[0],
                image_path=image_path,
                truth=truth_path.read_text(encoding="utf-8"),
            )
        )
    return cases


def load_image(path: Path) -> np.ndarray:
    """อ่าน PNG เป็น BGR uint8 ด้วย Qt ที่เป็น dependency อยู่แล้ว"""
    from PyQt6.QtGui import QImage

    image = QImage(str(path))
    if image.isNull():
        raise ValueError(f"อ่านภาพไม่ได้: {path}")
    image = image.convertToFormat(QImage.Format.Format_RGB32)
    ptr = image.constBits()
    ptr.setsize(image.sizeInBytes())
    stride = image.bytesPerLine() // 4
    buffer = np.frombuffer(ptr, dtype=np.uint8).reshape(image.height(), stride, 4)
    return np.ascontiguousarray(buffer[:, : image.width(), :3])


def run_case(engine, pipeline_name: str, case: Case) -> CaseResult:
    image = PIPELINES[pipeline_name](load_image(case.image_path))
    started = time.perf_counter()
    try:
        lines = engine.recognize(image)
    except Exception as exc:  # engine ล้มกับภาพเดียวไม่ควรล้มทั้งการทดสอบ
        lines = []
        print(f"  ! {engine.name}/{pipeline_name}/{case.name}: {exc}")
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    # กล่องยังไม่ได้ใช้ใน Phase 0 แต่ยืนยันไว้ว่าหารกลับได้จริง เพราะ Phase 3
    # ต้องพึ่งข้อนี้ ถ้า scale_factor ผิดจะได้รู้ตั้งแต่ตอนนี้
    factor = scale_factor_of(pipeline_name)
    assert factor >= 1

    hypothesis = "\n".join(ln.text for ln in lines)
    return CaseResult(
        engine=engine.name,
        pipeline=pipeline_name,
        name=case.name,
        group=case.group,
        word_accuracy=word_accuracy(case.truth, hypothesis),
        cer=character_error_rate(case.truth, hypothesis),
        elapsed_ms=elapsed_ms,
        text=hypothesis,
    )


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
    return ordered[index]


def summarize(results: list[CaseResult]) -> list[Summary]:
    buckets: dict[tuple[str, str, str], list[CaseResult]] = {}
    for item in results:
        buckets.setdefault((item.engine, item.pipeline, item.group), []).append(item)

    summaries = [
        Summary(
            engine=engine,
            pipeline=pipeline,
            group=group,
            mean_word_accuracy=statistics.fmean(r.word_accuracy for r in group_results),
            mean_cer=statistics.fmean(r.cer for r in group_results),
            p95_ms=_p95([r.elapsed_ms for r in group_results]),
            count=len(group_results),
        )
        for (engine, pipeline, group), group_results in buckets.items()
    ]
    return sorted(summaries, key=lambda s: (s.engine, s.pipeline, s.group))


def verdict(summaries: list[Summary]) -> tuple[bool, str, list[str]]:
    """คืน (ผ่านไหม, ชื่อ engine/pipeline ที่ดีที่สุด, เหตุผลรายข้อ)"""
    dialogue = [s for s in summaries if s.group == "dialogue"]
    if not dialogue:
        return False, "", ["ไม่มีผลของกลุ่ม dialogue เลย"]

    best = max(dialogue, key=lambda s: (s.mean_word_accuracy, -s.p95_ms))
    combo = f"{best.engine}/{best.pipeline}"

    reasons = []
    passed = True
    if best.mean_word_accuracy < DIALOGUE_ACCURACY_GATE:
        passed = False
        reasons.append(
            f"ไม่ผ่าน: dialogue word accuracy ดีที่สุดคือ "
            f"{best.mean_word_accuracy:.1%} ({combo}) ต้องได้ {DIALOGUE_ACCURACY_GATE:.0%}"
        )
    else:
        reasons.append(
            f"ผ่าน: dialogue word accuracy {best.mean_word_accuracy:.1%} ({combo})"
        )

    if best.p95_ms > LATENCY_P95_GATE_MS:
        passed = False
        reasons.append(
            f"ไม่ผ่าน: latency p95 {best.p95_ms:.0f} ms เกิน {LATENCY_P95_GATE_MS:.0f} ms"
        )
    else:
        reasons.append(f"ผ่าน: latency p95 {best.p95_ms:.0f} ms")

    menu = [
        s
        for s in summaries
        if s.group == "menu" and s.engine == best.engine and s.pipeline == best.pipeline
    ]
    if menu:
        accuracy = menu[0].mean_word_accuracy
        note = "ผ่าน" if accuracy >= MENU_ACCURACY_TARGET else "ต่ำกว่าเป้า (ไม่บล็อก)"
        reasons.append(f"{note}: menu word accuracy {accuracy:.1%}")

    return passed, combo, reasons


def render_report(summaries: list[Summary], results: list[CaseResult]) -> str:
    passed, combo, reasons = verdict(summaries)
    lines = [
        "# Phase 0 — ผลการวัด OCR กับ Persona 5",
        "",
        f"จำนวนภาพที่ทดสอบ: {len({r.name for r in results})} · "
        f"จำนวนการวัดทั้งหมด: {len(results)}",
        "",
        "## คำตัดสิน",
        "",
        f"**{'ผ่าน — เดินหน้า Task 10 ต่อได้' if passed else 'ไม่ผ่าน — หยุด กลับไปคุยกับผู้ใช้'}**",
        "",
    ]
    lines += [f"- {reason}" for reason in reasons]
    lines += [
        "",
        f"ค่าที่ควรใช้เป็นค่าเริ่มต้น: `{combo}`" if passed else "",
        "",
        "## ตารางผล",
        "",
        "| engine | pipeline | group | word acc | CER | p95 (ms) | n |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in summaries:
        lines.append(
            f"| {s.engine} | {s.pipeline} | {s.group} | "
            f"{s.mean_word_accuracy:.1%} | {s.mean_cer:.3f} | {s.p95_ms:.0f} | {s.count} |"
        )

    worst = sorted(results, key=lambda r: r.word_accuracy)[:10]
    lines += ["", "## 10 เคสที่แย่ที่สุด", ""]
    for r in worst:
        lines.append(
            f"- `{r.name}` {r.engine}/{r.pipeline} — {r.word_accuracy:.1%} — "
            f"อ่านได้ว่า: {r.text[:120]!r}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="เทียบ OCR engine สำหรับ Persona 5")
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    cases = load_cases(args.fixtures)
    if not cases:
        print(f"ไม่พบภาพทดสอบใน {args.fixtures} — ทำ Task 8 ให้เสร็จก่อน")
        return 1

    from waen.ocr.rapid_ocr import RapidOcrEngine
    from waen.ocr.windows_ocr import WindowsOcrEngine

    engines = []
    if WindowsOcrEngine.is_available():
        engines.append(WindowsOcrEngine())
    if RapidOcrEngine.is_available():
        engines.append(RapidOcrEngine())
    if len(engines) < 2:
        print(
            "เตือน: ใช้ได้แค่ engine เดียว การเทียบจะไม่มีความหมายเต็มที่ "
            "แก้ให้ครบทั้งสองตัวก่อนดีกว่า"
        )
    if not engines:
        print("ไม่มี OCR engine ที่ใช้งานได้เลย")
        return 1

    results: list[CaseResult] = []
    for engine in engines:
        for pipeline_name in PIPELINES:
            print(f"== {engine.name} / {pipeline_name} ({len(cases)} ภาพ)")
            for case in cases:
                results.append(run_case(engine, pipeline_name, case))

    summaries = summarize(results)
    report = render_report(summaries, results)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(report)

    passed, _, _ = verdict(summaries)
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
