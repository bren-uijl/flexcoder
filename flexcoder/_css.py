"""_css.py — resolves the path to flexcoder.tcss after pip install."""
from pathlib import Path
import importlib.resources as _res

def css_path() -> str:
    """Return absolute path to flexcoder.tcss, works both from source and after pip install."""
    try:
        # Python 3.9+ — works correctly after pip install
        ref = _res.files("flexcoder") / "flexcoder.tcss"
        with _res.as_file(ref) as p:
            return str(p)
    except Exception:
        # Fallback: relative to this file
        return str(Path(__file__).parent / "flexcoder.tcss")

CSS_PATH = css_path()
