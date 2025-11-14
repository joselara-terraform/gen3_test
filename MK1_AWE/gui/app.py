#!/usr/bin/env python3
"""MK1_AWE Control GUI Application"""

import sys
import logging
from PySide6.QtWidgets import QApplication
from main_window import MainWindow

# Suppress pymodbus noise - only show critical errors
logging.getLogger('pymodbus').setLevel(logging.CRITICAL)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

