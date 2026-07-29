from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QFileDialog, QMessageBox, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt
from gui.globals import signals

class GlobalLogWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(150)
        self.setStyleSheet("""
            QFrame { background-color: #0f172a; border-top: 1px solid #334155; }
            QTextEdit { background-color: #0f172a; color: #a5b4fc; font-family: monospace; font-size: 11px; border: none; }
            QPushButton { background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; border-radius: 4px; padding: 2px 8px; font-size: 10px; }
            QPushButton:hover { background-color: #334155; color: white; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("🐞 Debug Log")
        title.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 11px; border: none;")
        toolbar.addWidget(title)
        
        toolbar.addSpacerItem(QSpacerItem(40, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_log)
        toolbar.addWidget(clear_btn)
        
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.export_log)
        toolbar.addWidget(export_btn)
        
        layout.addLayout(toolbar)
        
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)
        
        signals.log_message.connect(self.append_log)
        
    def append_log(self, text: str):
        self.log_edit.append(text)
        sb = self.log_edit.verticalScrollBar()
        sb.setValue(sb.maximum())
        
    def clear_log(self):
        self.log_edit.clear()
        
    def export_log(self):
        content = self.log_edit.toPlainText()
        if not content:
            QMessageBox.warning(self, "Peringatan", "Log masih kosong.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Simpan File Log", "cliptzy_debug.log", "Log Files (*.log);;Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "Berhasil", f"Log berhasil disimpan di:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error Export", f"Gagal menyimpan log: {e}")
