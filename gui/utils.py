"""
GUI helper utilities for Cliptzy desktop application.
"""

import os
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QFont
from PyQt6.QtCore import Qt

def get_app_icon() -> QIcon:
    """Returns application QIcon from assets or generates a dynamic movie clip icon."""
    icon_path = os.path.join("images", "icon.png")
    if os.path.exists(icon_path):
        return QIcon(icon_path)

    # Dynamically generate a sleek 64x64 icon pixmap
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background circle
    painter.setBrush(QColor("#6366f1"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, 64, 64, 16, 16)

    # Play symbol triangle
    painter.setBrush(QColor("#ffffff"))
    font = QFont("Segoe UI", 26, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "🎬")

    painter.end()
    return QIcon(pixmap)
