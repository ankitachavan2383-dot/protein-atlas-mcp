"""Render a protein report dict as Markdown, HTML, or pass-through JSON."""
from __future__ import annotations

import json
from typing import Any


def _section(title: str, body: str) -> str:
    return f"## {title}\n\n{body}\n" if body else f"## {title}\n\n_No data available._\n"


def report_to_markdown(report: dict[str, Any]) -> str:
    basic = report.get("basic_info", {}) or {}
    lines = [f"# Protein Report: {basic.get('protein_name') or basic.get('query', 'Unknown')}", ""]

    lines.append(
        _section(
            "Basic Info",
            "\n".join(
                f"- **{k.replace('_', ' ').title()}:** {v}"
                for k, v in basic.items()
                if v not in (None, [], "")
            ),
        )
    )

    seq = report.get("sequence", {}) or {}
    if seq.get("sequence"):
        seq_preview = seq["sequence"][:60] + ("..." if len(seq["sequence"]) > 60 else "")
        lines.append(_section("Sequence", f"- **Length:** {seq.get('length')}\n- **Preview:** `{seq_preview}`"))

    domains = report.get("domains", []) or []
    if domains:
        rows = "\n".join(f"- {d.get('name')} ({d.get('start')}-{d.get('end')})" for d in domains)
        lines.append(_section("Domains", rows))
    else:
        lines.append(_section("Domains", ""))

    structure = report.get("structure", {}) or {}
    lines.append(
        _section(
            "Structure",
            "\n".join(f"- **{k.replace('_', ' ').title()}:** {v}" for k, v in structure.items() if v),
        )
    )

    interactions = report.get("interactions", []) or []
    if interactions:
        rows = "\n".join(
            f"- {i.get('partner')} (confidence: {i.get('confidence')})" for i in interactions[:15]
        )
        lines.append(_section("Interactions", rows))
    else:
        lines.append(_section("Interactions", ""))

    pathways = report.get("pathways", []) or []
    if pathways:
        rows = "\n".join(f"- {p.get('name')} ({p.get('id')})" for p in pathways)
        lines.append(_section("Pathways", rows))
    else:
        lines.append(_section("Pathways", ""))

    diseases = report.get("diseases", []) or []
    if diseases:
        rows = "\n".join(f"- {d.get('title') or d.get('name')}" for d in diseases[:15])
        lines.append(_section("Disease Associations", rows))
    else:
        lines.append(_section("Disease Associations", ""))

    papers = report.get("publications", []) or []
    if papers:
        rows = "\n".join(f"- {p.get('title')} ({p.get('pub_date')}) - {p.get('url')}" for p in papers[:10])
        lines.append(_section("Publications", rows))
    else:
        lines.append(_section("Publications", ""))

    lines.append(_section("Summary", report.get("summary", "")))

    return "\n".join(lines)


def report_to_html(report: dict[str, Any]) -> str:
    markdown_body = report_to_markdown(report)
    # Minimal markdown->HTML for headings/bullets/bold/code is enough here;
    # for anything richer, pipe `markdown_body` through a real MD renderer.
    html_lines = ["<!DOCTYPE html>", "<html><head><meta charset='utf-8'>",
                  "<title>Protein Report</title></head><body>"]
    for line in markdown_body.splitlines():
        if line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("- "):
            html_lines.append(f"<li>{line[2:]}</li>")
        elif line.strip():
            html_lines.append(f"<p>{line}</p>")
    html_lines.append("</body></html>")
    return "\n".join(html_lines)


def report_to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, default=str)
