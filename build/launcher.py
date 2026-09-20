"""PyInstaller entry point.

``waen/__main__.py`` uses relative imports, which fail when PyInstaller runs it
as a top-level script, so the frozen exe starts here instead.
"""

from waen.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
