import os
import sys
from PyQt6.QtWidgets import QApplication
from app_controller import ApplicationController

APP_DIR = os.path.dirname(os.path.abspath(__file__))


def set_macos_icon():
    if sys.platform != 'darwin':
        return
    try:
        from AppKit import NSImage, NSApplication

        icon_path = os.path.join(APP_DIR, 'icon.png')
        if os.path.exists(icon_path):
            image = NSImage.alloc().initWithContentsOfFile_(icon_path)
            NSApplication.sharedApplication().setApplicationIconImage_(image)
    except ImportError:
        print('[!] Warning: PyObjC is not installed. Dock icon cannot be set on macOS.')
    except Exception as error:
        print(f'[!] Error setting Dock icon on macOS: {error}')


def main():
    app = QApplication(sys.argv)
    set_macos_icon()
    controller = ApplicationController()
    controller.start()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()