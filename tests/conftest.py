from pathlib import Path
import shutil
import pytest

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def pixel(tmp_path):
    root=tmp_path/'project'
    shutil.copytree(ROOT/'examples/pixel16',root,ignore=shutil.ignore_patterns('.mfai','output'))
    return root

@pytest.fixture
def vector(tmp_path):
    root=tmp_path/'vector'
    shutil.copytree(ROOT/'examples/vector',root,ignore=shutil.ignore_patterns('.mfai','output'))
    return root
