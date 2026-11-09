from pathlib import Path

import pytest

import render_resume as rr

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def data():
    return rr.load_resume(ROOT / "resume.yaml")


def test_example_is_fictional(data):
    assert data["basics"]["name"] == "Alex Example"
    assert data["basics"]["email"].endswith("@example.com")


def test_html_structure(data):
    out = rr.render_html(data)
    assert out.startswith("<!doctype html>")
    assert '<html lang="en" dir="ltr">' in out
    assert "<h1>Alex Example</h1>" in out
    assert "@page" in out and "size: A4" in out and "@media print" in out
    for section in data["sections"]:
        assert f"<h2>{section['title']}</h2>" in out
    assert "Vazirmatn:wght" not in out


def test_html_has_no_tables_or_images(data):
    # ATS-friendly: plain semantic text, no layout tables or images.
    out = rr.render_html(data)
    assert "<table" not in out and "<img" not in out


def test_rtl_override_adds_font(data):
    out = rr.render_html(data, direction="rtl")
    assert 'dir="rtl"' in out
    assert "fonts.googleapis.com/css2?family=Vazirmatn" in out


def test_persian_example_is_rtl():
    fa = rr.load_resume(ROOT / "examples" / "resume-fa.yaml")
    out = rr.render_html(fa)
    assert '<html lang="fa" dir="rtl">' in out
    assert "الکس نمونه" in out


def test_html_escaping(data):
    data["basics"]["name"] = "<script>alert(1)</script>"
    out = rr.render_html(data)
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_markdown(data):
    md = rr.render_markdown(data)
    assert md.startswith("# Alex Example\n")
    assert "## Experience" in md
    assert "### Senior Backend Engineer — Placeholder Corp, Remote" in md
    assert "- **Languages:** Python, SQL, JavaScript" in md
    assert "[demo-cli](https://example.com/demo-cli)" in md
    assert md.endswith("\n") and not md.endswith("\n\n")


@pytest.mark.parametrize(
    "bad",
    [
        [],
        {"basics": {}},
        {"basics": {"name": "X"}, "meta": {"direction": "up"}},
        {"basics": {"name": "X"}, "sections": [{"title": "S", "type": "grid"}]},
        {"basics": {"name": "X"}, "sections": [{"type": "list"}]},
    ],
)
def test_validation_errors(bad):
    with pytest.raises(rr.ResumeError):
        rr.validate(bad)


def test_cli_writes_files(tmp_path, capsys):
    code = rr.main([str(ROOT / "resume.yaml"), "-o", str(tmp_path)])
    assert code == 0
    assert (tmp_path / "resume.html").read_text(encoding="utf-8").startswith("<!doctype html>")
    assert (tmp_path / "resume.md").exists()
    assert "wrote" in capsys.readouterr().out


def test_cli_bad_file(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("basics: {}\n", encoding="utf-8")
    assert rr.main([str(bad), "-o", str(tmp_path)]) == 1
    assert "basics.name is required" in capsys.readouterr().err
