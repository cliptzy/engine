from PyQt6.QtCore import QObject, pyqtSignal

class GlobalSignals(QObject):
    log_message = pyqtSignal(str)
    log_message_inline = pyqtSignal(str)

signals = GlobalSignals()
