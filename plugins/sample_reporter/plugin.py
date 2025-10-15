# plugins/sample_reporter/plugin.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class SampleReporterWidget(QWidget):
    def __init__(self, keyring_data, save_callback, main_window):
        super().__init__()
        self.setWindowTitle("Sample Reporter Info")
        
        layout = QVBoxLayout(self)
        label = QLabel("This is the desktop component of the Sample Reporter.\n"
                       "Its main functionality is integrated into the Web Panel.")
        layout.addWidget(label)