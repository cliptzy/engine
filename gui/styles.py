"""
Modern Dark Theme QSS for Cliptzy Desktop Application
"""

DARK_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #0f172a;
    color: #f8fafc;
    font-family: 'Segoe UI', 'Inter', system-ui, sans-serif;
}

QWidget {
    font-family: 'Segoe UI', 'Inter', system-ui, sans-serif;
    color: #f8fafc;
}

/* Card Containers */
QFrame[class="card"] {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
}

/* Labels */
QLabel {
    color: #f8fafc;
    font-size: 13px;
}

QLabel[class="title"] {
    font-size: 18px;
    font-weight: bold;
    color: #818cf8;
}

QLabel[class="section-header"] {
    font-size: 14px;
    font-weight: 600;
    color: #c7d2fe;
}

QLabel[class="muted"] {
    color: #94a3b8;
    font-size: 12px;
}

/* Text Inputs & Combo Boxes */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 6px 10px;
    color: #f8fafc;
    font-size: 13px;
    selection-background-color: #6366f1;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #6366f1;
    background-color: #1e1b4b;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #1e293b;
    border: 1px solid #334155;
    selection-background-color: #6366f1;
    color: #f8fafc;
}

/* Push Buttons */
QPushButton {
    background-color: #334155;
    color: #f8fafc;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #475569;
}

QPushButton:pressed {
    background-color: #1e293b;
}

QPushButton[class="primary"] {
    background-color: #6366f1;
    color: #ffffff;
}

QPushButton[class="primary"]:hover {
    background-color: #4f46e5;
}

QPushButton[class="primary"]:pressed {
    background-color: #4338ca;
}

QPushButton[class="success"] {
    background-color: #10b981;
    color: #ffffff;
}

QPushButton[class="success"]:hover {
    background-color: #059669;
}

QPushButton[class="danger"] {
    background-color: #ef4444;
    color: #ffffff;
}

QPushButton[class="danger"]:hover {
    background-color: #dc2626;
}

QPushButton:disabled {
    background-color: #1e293b;
    color: #64748b;
}

/* Checkboxes & Radio Buttons */
QCheckBox, QRadioButton {
    spacing: 8px;
    font-size: 13px;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #0f172a;
}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #6366f1;
    border-color: #6366f1;
}

/* Progress Bar */
QProgressBar {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
    font-size: 12px;
}

QProgressBar::chunk {
    background-color: #6366f1;
    border-radius: 7px;
}

/* List Widgets & Tree View */
QListWidget {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 4px;
}

QListWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
    margin-bottom: 4px;
}

QListWidget::item:hover {
    background-color: #1e293b;
}

QListWidget::item:selected {
    background-color: #312e81;
    color: #a5b4fc;
}

/* Text Edit / Log Console */
QTextEdit {
    background-color: #020617;
    border: 1px solid #1e293b;
    border-radius: 8px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    color: #38bdf8;
    padding: 8px;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #0f172a;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #334155;
    border-radius: 8px;
    background-color: #1e293b;
}

QTabBar::tab {
    background-color: #0f172a;
    border: 1px solid #334155;
    padding: 8px 16px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 4px;
}

QTabBar::tab:selected {
    background-color: #1e293b;
    border-bottom: 2px solid #6366f1;
    color: #818cf8;
    font-weight: bold;
}
"""
