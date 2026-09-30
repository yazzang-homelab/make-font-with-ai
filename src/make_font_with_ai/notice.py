"""One-time GitHub star request, shown on the first interactive CLI run after installation."""
from __future__ import annotations
import os
import sys
from pathlib import Path

REPO_URL = 'https://github.com/yazzang-homelab/make-font-with-ai'
MARKER_NAME = 'star-notice-shown'
MESSAGE = (
    '\n'
    'make-font-with-ai가 설치되었습니다. 도움이 되었다면 GitHub star 하나 부탁드립니다.\n'
    'If this tool is useful to you, please consider starring the repository:\n'
    f'  {REPO_URL}\n'
    '(이 안내는 한 번만 표시됩니다 / this notice is shown only once)\n'
)


def marker_path() -> Path:
    """Per-user marker so the notice is shown once per machine, not once per project."""
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA') or os.environ.get('LOCALAPPDATA') or str(Path.home())
    else:
        base = os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
    return Path(base) / 'make-font-with-ai' / MARKER_NAME


def show_star_notice_once(*, path: Path | None = None, stream=None, interactive: bool | None = None) -> bool:
    """Print the star request once. Returns True when it was printed.

    Non-interactive streams (CI, pipes, agent hosts) neither print nor mark, so the first
    real human run still sees it. Any filesystem failure is swallowed: the notice must never
    break a font build.
    """
    if os.environ.get('MFAI_NO_STAR_NOTICE'):
        return False
    stream = sys.stderr if stream is None else stream
    if interactive is None:
        interactive = bool(getattr(stream, 'isatty', lambda: False)())
    if not interactive:
        return False
    path = marker_path() if path is None else path
    try:
        if path.exists():
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(REPO_URL + '\n', encoding='utf-8')
    except OSError:
        return False
    try:
        stream.write(MESSAGE)
        stream.flush()
    except (OSError, ValueError):
        pass
    return True
