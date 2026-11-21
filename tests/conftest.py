import sys
from pathlib import Path

# Permite importar os módulos de src/ nos testes
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
