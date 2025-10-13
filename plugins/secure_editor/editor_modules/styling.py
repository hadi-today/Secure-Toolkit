DARK_STYLESHEET = """
QWidget {
    background-color: #2b2b2b;
    color: #f0f0f0;
    font-family: Arial;
}
QTextEdit {
    background-color: #3c3c3c;
    border: 1px solid #555;
    font-size: 14px;
    padding: 10px;
}
QPushButton {
    background-color: #555;
    border: 1px solid #666;
    padding: 8px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #666;
}
QToolBar {
    background-color: #3c3c3c;
    border: none;
}
QStatusBar {
    font-size: 12px;
}
"""

LIGHT_STYLESHEET = "" 

def apply_theme(app, theme_name):
    if theme_name == "dark":
        app.setStyleSheet(DARK_STYLESHEET)
    else:
        app.setStyleSheet(LIGHT_STYLESHEET)