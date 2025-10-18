from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class SampleReporterWidget(QWidget):
    def __init__(self, keyring_data, save_callback, main_window):
        super().__init__()
        self.setWindowTitle('Sample Reporter Info')

        layout = QVBoxLayout(self)
        label = QLabel(
            'This is the desktop companion for the Sample Reporter plugin.\n'
            'Its primary features live in the Web Panel interface.'
        )
        layout.addWidget(label)

