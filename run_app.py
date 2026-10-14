"""Launcher script used as the PyInstaller entry point (it cannot start from a package's __main__)."""

import sys

from pdftool.app import main

if __name__ == "__main__":
    sys.exit(main())
