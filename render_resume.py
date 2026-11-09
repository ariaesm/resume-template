"""Render a YAML resume to standalone HTML (print-ready, A4) and Markdown.

No template engine is required: HTML is built with ``string.Template`` and
small helper functions, so the only dependency is PyYAML.
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path
from string import Template
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
DEFAULT_CSS = HERE / "style.css"
SECTION_TYPES = ("entries", "tags", "list")
VAZIRMATN_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" '
    'href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700&display=swap">'
)

PAGE = Template(
    """<!doctype html>
<html lang="$lang" dir="$direction">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
$fonts
<style>
$css
</style>
</head>
<body>
<main class="page">
$body
</main>
</body>
</html>
"""
)


class ResumeError(ValueError):
    """Raised when the resume data does not match the expected schema."""


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def load_resume(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    validate(data)
    return data


def validate(data: Any) -> None:
    if not isinstance(data, dict):
        raise ResumeError("resume root must be a mapping")
    basics = data.get("basics")
    if not isinstance(basics, dict) or not basics.get("name"):
        raise ResumeError("basics.name is required")
    direction = data.get("meta", {}).get("direction", "ltr")
    if direction not in ("ltr", "rtl"):
        raise ResumeError(f"meta.direction must be 'ltr' or 'rtl', got {direction!r}")
    for i, section in enumerate(data.get("sections", []) or []):
        if not isinstance(section, dict) or not section.get("title"):
            raise ResumeError(f"sections[{i}] needs a title")
        kind = section.get("type", "entries")
        if kind not in SECTION_TYPES:
            raise ResumeError(f"sections[{i}].type must be one of {SECTION_TYPES}, got {kind!r}")
        if not isinstance(section.get("items", []), list):
            raise ResumeError(f"sections[{i}].items must be a list")


def resolve_direction(data: dict, override: str | None = None) -> str:
    if override:
        return override
    return data.get("meta", {}).get("direction", "ltr")


# --------------------------------------------------------------------- HTML


def _link(url: str, text: str) -> str:
    return f'<a href="{esc(url)}">{esc(text)}</a>'


def _contact_items(basics: dict) -> list[str]:
    items = []
    if basics.get("email"):
        items.append(_link(f"mailto:{basics['email']}", basics["email"]))
    if basics.get("phone"):
        tel = "".join(ch for ch in str(basics["phone"]) if ch.isdigit() or ch == "+")
        items.append(_link(f"tel:{tel}", basics["phone"]))
    if basics.get("location"):
        items.append(esc(basics["location"]))
    for link in basics.get("links", []) or []:
        items.append(_link(link["url"], link.get("label", link["url"])))
    return items


def _header_html(basics: dict) -> str:
    parts = ["<header>", f"<h1>{esc(basics['name'])}</h1>"]
    if basics.get("label"):
        parts.append(f'<p class="label">{esc(basics["label"])}</p>')
    contacts = _contact_items(basics)
    if contacts:
        lis = "".join(f'<li dir="auto">{c}</li>' for c in contacts)
        parts.append(f'<ul class="contact">{lis}</ul>')
    parts.append("</header>")
    if basics.get("summary"):
        parts.append(f'<p class="summary">{esc(basics["summary"])}</p>')
    return "\n".join(parts)


def _entry_html(item: dict) -> str:
    heading = esc(item.get("heading", ""))
    if item.get("url"):
        heading = _link(item["url"], item.get("heading", item["url"]))
    sub = [esc(x) for x in (item.get("subheading"), item.get("location")) if x]
    out = ['<div class="entry">', '<div class="entry-head">', f"<h3>{heading}</h3>"]
    if item.get("date"):
        out.append(f'<span class="date">{esc(item["date"])}</span>')
    out.append("</div>")
    if sub:
        out.append(f'<div class="sub">{" · ".join(sub)}</div>')
    bullets = item.get("bullets") or []
    if bullets:
        lis = "".join(f"<li>{esc(b)}</li>" for b in bullets)
        out.append(f'<ul class="bullets">{lis}</ul>')
    out.append("</div>")
    return "\n".join(out)


def _section_html(section: dict) -> str:
    kind = section.get("type", "entries")
    items = section.get("items", []) or []
    out = [f'<section class="{kind}">', f"<h2>{esc(section['title'])}</h2>"]
    if kind == "entries":
        out.extend(_entry_html(i) for i in items)
    elif kind == "tags":
        for item in items:
            values = ", ".join(esc(v) for v in item.get("values", []))
            out.append(f"<p><strong>{esc(item.get('label', ''))}:</strong> {values}</p>")
    else:  # list
        lis = "".join(f"<li>{esc(i)}</li>" for i in items)
        out.append(f'<ul class="plain">{lis}</ul>')
    out.append("</section>")
    return "\n".join(out)


def render_html(data: dict, direction: str | None = None, css: str | None = None) -> str:
    validate(data)
    direction = resolve_direction(data, direction)
    lang = data.get("meta", {}).get("lang", "fa" if direction == "rtl" else "en")
    if css is None:
        css = DEFAULT_CSS.read_text(encoding="utf-8")
    body = [_header_html(data["basics"])]
    body.extend(_section_html(s) for s in data.get("sections", []) or [])
    return PAGE.substitute(
        lang=esc(lang),
        direction=direction,
        title=esc(f"{data['basics']['name']} – Resume"),
        fonts=VAZIRMATN_LINK if direction == "rtl" else "",
        css=css.strip(),
        body="\n".join(body),
    )


# ----------------------------------------------------------------- Markdown


def _md_link(url: str, text: str) -> str:
    return f"[{text}]({url})"


def render_markdown(data: dict) -> str:
    validate(data)
    basics = data["basics"]
    lines = [f"# {basics['name']}", ""]
    if basics.get("label"):
        lines += [f"**{basics['label']}**", ""]
    contacts = []
    if basics.get("email"):
        contacts.append(basics["email"])
    if basics.get("phone"):
        contacts.append(str(basics["phone"]))
    if basics.get("location"):
        contacts.append(basics["location"])
    for link in basics.get("links", []) or []:
        contacts.append(_md_link(link["url"], link.get("label", link["url"])))
    if contacts:
        lines += [" · ".join(contacts), ""]
    if basics.get("summary"):
        lines += [basics["summary"], ""]
    for section in data.get("sections", []) or []:
        kind = section.get("type", "entries")
        lines += [f"## {section['title']}", ""]
        for item in section.get("items", []) or []:
            if kind == "entries":
                heading = item.get("heading", "")
                if item.get("url"):
                    heading = _md_link(item["url"], heading)
                meta = [x for x in (item.get("subheading"), item.get("location")) if x]
                title = f"### {heading}"
                if meta:
                    title += f" — {', '.join(meta)}"
                lines.append(title)
                if item.get("date"):
                    lines.append(f"*{item['date']}*")
                lines.append("")
                for bullet in item.get("bullets") or []:
                    lines.append(f"- {bullet}")
                if item.get("bullets"):
                    lines.append("")
            elif kind == "tags":
                lines.append(f"- **{item.get('label', '')}:** {', '.join(item.get('values', []))}")
            else:
                lines.append(f"- {item}")
        if kind != "entries":
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a YAML resume to HTML and Markdown.")
    parser.add_argument("resume", nargs="?", default="resume.yaml", help="path to resume YAML")
    parser.add_argument("-o", "--out-dir", default="out", help="output directory (default: out)")
    parser.add_argument("--rtl", action="store_true", help="force right-to-left layout")
    parser.add_argument("--ltr", action="store_true", help="force left-to-right layout")
    parser.add_argument("--css", help="custom stylesheet to inline instead of style.css")
    args = parser.parse_args(argv)
    if args.rtl and args.ltr:
        parser.error("--rtl and --ltr are mutually exclusive")

    try:
        data = load_resume(args.resume)
    except (OSError, yaml.YAMLError, ResumeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    direction = "rtl" if args.rtl else "ltr" if args.ltr else None
    css = Path(args.css).read_text(encoding="utf-8") if args.css else None
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(args.resume).stem
    html_path = out / f"{stem}.html"
    md_path = out / f"{stem}.md"
    html_path.write_text(render_html(data, direction, css), encoding="utf-8")
    md_path.write_text(render_markdown(data), encoding="utf-8")
    print(f"wrote {html_path}")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
