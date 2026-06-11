from pathlib import Path

def read_mfile(filepath: str) -> str:
    """Reads content of a MATLAB script file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Script not found: {filepath}")
    
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()