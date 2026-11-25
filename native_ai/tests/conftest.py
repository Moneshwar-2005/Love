import sys
from pathlib import Path

# F:\LOVE must be on sys.path so 'import native_ai' resolves to F:\LOVE\native_ai
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

native_ai_dir = Path(__file__).resolve().parent.parent
if str(native_ai_dir) not in sys.path:
    sys.path.insert(0, str(native_ai_dir))
