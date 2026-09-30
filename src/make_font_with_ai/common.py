"""Small, fail-closed helpers. Project JSON is data, never executable code."""
from __future__ import annotations
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

class GateError(RuntimeError):
    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f'{code}: {detail}')

def require(value: bool, code: str, detail: str) -> None:
    if not value:
        raise GateError(code, detail)

def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def read_json(path: Path, limit: int = 100_000_000) -> Any:
    require(path.is_file(), 'MISSING_FILE', str(path))
    require(path.stat().st_size <= limit, 'FILE_TOO_LARGE', str(path))
    def unique(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, 'DUPLICATE_JSON_KEY', key)
            out[key] = value
        return out
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=unique,
                          parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    except (UnicodeError, ValueError) as exc:
        raise GateError('INVALID_JSON', f'{path.name}: {exc}') from exc

def safe_path(root: Path, value: str, *, exists: bool = True) -> Path:
    require(isinstance(value, str) and bool(value), 'INVALID_PATH', 'Expected a relative path')
    w = PureWindowsPath(value)
    require(not w.drive and not w.is_absolute() and '\\' not in value and '\x00' not in value,
            'PATH_ESCAPE', value)
    p = Path(value)
    require(not p.is_absolute() and '..' not in p.parts, 'PATH_ESCAPE', value)
    target = (root / p).resolve()
    require(target.is_relative_to(root.resolve()), 'PATH_ESCAPE', value)
    if exists:
        require(target.is_file(), 'MISSING_FILE', value)
    return target

def atomic_bytes(path: Path, data: bytes, *, overwrite: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite and path.exists():
        require(path.is_file() and path.read_bytes() == data, 'OUTPUT_EXISTS', str(path))
        return
    fd, name = tempfile.mkstemp(prefix='.mfai-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if overwrite:
            os.replace(name, path)
        else:
            # Hard link is atomic and refuses replacement on POSIX and Windows NTFS.
            try:
                os.link(name, path)
            except FileExistsError:
                require(path.read_bytes() == data, 'OUTPUT_EXISTS', str(path))
    finally:
        if os.path.exists(name):
            os.unlink(name)

def write_json(path: Path, data: Any) -> None:
    atomic_bytes(path, json.dumps(data, ensure_ascii=False, indent=2,
                                 allow_nan=False).encode('utf-8') + b'\n')

def engine_signature() -> str:
    """Installation paths, CRLF and Python cache files do not change source identity."""
    root = Path(__file__).parent
    records = []
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.suffix in ('.py', '.json') and '__pycache__' not in p.parts:
            data = p.read_bytes().replace(b'\r\n', b'\n')
            records.append([p.relative_to(root).as_posix(), sha(data)])
    return digest(records)
