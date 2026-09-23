"""Run with:  pip install pytest && pytest -q   (from the task4.4-csv-profiler folder)"""
import json

from csvprofiler.cli import main
from csvprofiler.history import History
from csvprofiler.profiler import profile_csv


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_numeric_and_text_columns(tmp_path):
    p = _write(tmp_path, "a.csv", "unit,score\nSWE40006,80\nSWE40006,90\nCOS40005,\n")
    prof = profile_csv(p)
    assert prof["rows"] == 3 and prof["columns"] == 2
    unit, score = prof["column_profiles"]
    assert unit["type"] == "text" and unit["top_values"][0] == ("SWE40006", 2)
    assert score["type"] == "numeric" and score["missing"] == 1
    assert score["mean"] == 85 and score["min"] == 80 and score["max"] == 90


def test_semicolon_delimiter_detected(tmp_path):
    p = _write(tmp_path, "b.csv", "a;b\n1;2\n3;4\n")
    assert profile_csv(p)["columns"] == 2


def test_profile_all_writes_reports_and_history(tmp_path):
    inp, out, db = tmp_path / "in", tmp_path / "out", tmp_path / "h.db"
    inp.mkdir()
    _write(inp, "x.csv", "a,b\n1,2\n")
    code = main(["profile-all", "--input", str(inp), "--output", str(out), "--db", str(db)])
    assert code == 0
    assert json.loads((out / "x.profile.json").read_text())["rows"] == 1
    assert (out / "x.profile.md").exists()
    h = History(db)
    assert h.recent()[0][3] == "x.csv"
    h.close()


def test_missing_input_returns_exit_code_3(tmp_path):
    code = main(["profile", "nope.csv", "--input", str(tmp_path), "--output", str(tmp_path), "--db", str(tmp_path / "h.db")])
    assert code == 3


def test_empty_folder_returns_exit_code_4(tmp_path):
    code = main(["profile-all", "--input", str(tmp_path), "--output", str(tmp_path / "o"), "--db", str(tmp_path / "h.db")])
    assert code == 4


def test_unwritable_output_returns_exit_code_5(tmp_path, monkeypatch):
    import csvprofiler.cli as cli
    inp = tmp_path / "in"
    inp.mkdir()
    _write(inp, "x.csv", "a\n1\n")
    monkeypatch.setattr(cli, "_output_writable", lambda _p: False)
    code = main(["profile-all", "--input", str(inp), "--output", str(tmp_path / "o"), "--db", str(tmp_path / "h.db")])
    assert code == 5
