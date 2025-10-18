from textwrap import dedent

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('About Secure Toolkit')
        self.setFixedSize(420, 360)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title_label = QLabel('Secure Toolkit')
        title_label.setStyleSheet('font-size: 20px; font-weight: bold;')
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        version_label = QLabel('Version 1.1')
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        desc_label = QLabel(
            'A modular desktop toolbox for secure key management, document workflows, '
            'and everyday cryptography powered by Python and PyQt6.'
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignJustify)
        desc_label.setWordWrap(True)

        whats_new_label = QLabel(
            dedent(
                """
                <b>What&apos;s new in v1.1</b>
                <ul style="margin-left:16px;">
                    <li>Dedicated windows per plugin keep workflows focused and service states visible.</li>
                    <li>Updated copy across the app clarifies flows and guidance in plain English.</li>
                    <li>Fresh key vault and secure notes overviews surface key health and version history.</li>
                    <li>A unified launch routine prevents layout collisions and produces a steadier startup.</li>
                </ul>
                """
            ).strip()
        )
        whats_new_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        whats_new_label.setWordWrap(True)

        link_label = QLabel('<a href="https://hadi.ge">hadi.ge</a>')
        link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link_label.setOpenExternalLinks(True)

        close_button = QPushButton('Close')
        close_button.clicked.connect(self.accept)

        layout.addWidget(title_label)
        layout.addWidget(version_label)
        layout.addWidget(desc_label)
        layout.addWidget(whats_new_label)
        layout.addStretch()
        layout.addWidget(link_label)
        layout.addWidget(close_button)
