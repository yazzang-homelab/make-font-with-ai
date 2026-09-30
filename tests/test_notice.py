import io
import json
from make_font_with_ai import cli
from make_font_with_ai.notice import REPO_URL, show_star_notice_once


def test_star_notice_prints_once_then_stays_silent(tmp_path):
    marker = tmp_path / 'cfg' / 'star-notice-shown'
    first = io.StringIO()
    assert show_star_notice_once(path=marker, stream=first, interactive=True)
    assert REPO_URL in first.getvalue() and marker.is_file()
    second = io.StringIO()
    assert not show_star_notice_once(path=marker, stream=second, interactive=True)
    assert second.getvalue() == ''


def test_star_notice_skips_non_interactive_without_marking(tmp_path):
    marker = tmp_path / 'star-notice-shown'
    out = io.StringIO()
    assert not show_star_notice_once(path=marker, stream=out, interactive=False)
    assert out.getvalue() == '' and not marker.exists()


def test_star_notice_opt_out_env(tmp_path, monkeypatch):
    monkeypatch.setenv('MFAI_NO_STAR_NOTICE', '1')
    marker = tmp_path / 'star-notice-shown'
    assert not show_star_notice_once(path=marker, stream=io.StringIO(), interactive=True)
    assert not marker.exists()


def test_star_notice_unwritable_marker_never_breaks_cli(tmp_path):
    blocker = tmp_path / 'file'
    blocker.write_text('x')
    marker = blocker / 'star-notice-shown'  # parent is a file: mkdir fails
    assert not show_star_notice_once(path=marker, stream=io.StringIO(), interactive=True)


def test_doctor_stdout_stays_pure_json_when_notice_shown(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv('MFAI_NO_STAR_NOTICE', raising=False)
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    monkeypatch.setenv('APPDATA', str(tmp_path))
    monkeypatch.setattr('sys.stderr.isatty', lambda: True, raising=False)
    assert cli.main(['doctor']) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)['mfai']
    assert REPO_URL in captured.err
    assert cli.main(['doctor']) == 0
    assert REPO_URL not in capsys.readouterr().err
