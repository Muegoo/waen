"""Render real overlay widgets over original synthetic example text."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter
from PyQt6.QtWidgets import QApplication

from waen.config import OverlayConfig
from waen.geometry import Box
from waen.models import OverlayItem
from waen.ui.overlay import OverlayWindow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("docs/images"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for name in ("tahoma.ttf", "tahomabd.ttf", "LeelawUI.ttf", "arial.ttf"):
        if (fonts / name).is_file():
            QFontDatabase.addApplicationFont(str(fonts / name))
    examples = [
        ("The next chapter starts here.", "บทต่อไปเริ่มต้นที่นี่"),
        ("Take a moment. Your progress is saved.", "พักสักครู่ ความคืบหน้าของคุณถูกบันทึกแล้ว"),
        ("Choose your path and keep moving forward.", "เลือกเส้นทางของคุณแล้วก้าวต่อไป"),
    ]
    frames = []
    for english, thai in examples:
        for translated in (False, True):
            base = QImage(1280, 720, QImage.Format.Format_ARGB32)
            base.fill(QColor("#101c29"))
            painter = QPainter(base)
            painter.setPen(QColor("#77d6b2"))
            painter.setFont(QFont("Tahoma", 18))
            painter.drawText(72, 70, "waen / แว่น")
            painter.setPen(QColor("#f0f5fa"))
            painter.setFont(QFont("Tahoma", 32, QFont.Weight.Bold))
            painter.drawText(72, 140, "English text. Thai overlay.")
            painter.setFont(QFont("Tahoma", 15))
            painter.setPen(QColor("#9dafc1"))
            painter.drawText(72, 185, "Original synthetic examples · actual Qt overlay renderer")
            painter.fillRect(72, 420, 1136, 120, QColor("#1c3042"))
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Tahoma", 24))
            painter.drawText(100, 485, english)
            painter.setPen(QColor("#9dafc1"))
            painter.setFont(QFont("Tahoma", 12))
            painter.drawText(72, 605, "Fixed example translations · no live OCR or translation service call")
            painter.drawText(72, 635, "Capture → OCR → stabilization → translation → overlay")
            painter.end()

            overlay = OverlayWindow(Box(0, 0, 1280, 720), 1.0, OverlayConfig())
            if translated:
                overlay.set_items([OverlayItem(english, thai, Box(72, 420, 1136, 120), Box(72, 306, 1136, 84), 24)])
            transparent = QImage(1280, 720, QImage.Format.Format_ARGB32)
            transparent.fill(Qt.GlobalColor.transparent)
            overlay.render(transparent)
            painter = QPainter(base)
            painter.drawImage(0, 0, transparent)
            painter.end()
            if not base.save(str(args.out / "overlay-preview.png")):
                raise RuntimeError("Could not save preview")
            pointer = base.constBits()
            pointer.setsize(base.sizeInBytes())
            frames.append(Image.frombytes("RGBA", (1280, 720), bytes(pointer), "raw", "BGRA").convert("RGB"))
            overlay.close()
            app.processEvents()
    frames[0].save(args.out / "overlay-preview.gif", save_all=True, append_images=frames[1:], duration=[900, 2100]*3, loop=0)
    print("Rendered synthetic overlay preview and GIF.")


if __name__ == "__main__":
    main()
