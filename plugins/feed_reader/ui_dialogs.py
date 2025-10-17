# File: ui_dialogs.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox, 
                             QFormLayout, QSpinBox)
# این خط اصلاح شده و صحیح است
from .constants import DEFAULT_FETCH_DAYS

class AddFeedDialog(QDialog):
    def __init__(self, parent=None, feed_data=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_input = QLineEdit(self)
        self.url_input = QLineEdit(self)
        self.tz_input = QLineEdit(self)
        self.days_input = QSpinBox(self)
        self.days_input.setRange(1, 9999)
        self.days_input.setSuffix(" days")

        if feed_data:
            self.setWindowTitle("Edit Feed")
            self.name_input.setText(feed_data.get('name', ''))
            self.url_input.setText(feed_data.get('url', ''))
            self.tz_input.setText(feed_data.get('timezone', 'Asia/Tbilisi'))
            self.days_input.setValue(feed_data.get('fetch_days', DEFAULT_FETCH_DAYS))
        else:
            self.setWindowTitle("Add New Feed")
            self.tz_input.setText("Asia/Tbilisi")
            self.days_input.setValue(DEFAULT_FETCH_DAYS)

        form_layout.addRow("Feed Name:", self.name_input)
        form_layout.addRow("Feed URL:", self.url_input)
        form_layout.addRow("Timezone:", self.tz_input)
        form_layout.addRow("Fetch Last:", self.days_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addLayout(form_layout); layout.addWidget(buttons)

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "url": self.url_input.text().strip(),
            "timezone": self.tz_input.text().strip(),
            "fetch_days": self.days_input.value()
        }