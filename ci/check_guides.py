#!/usr/bin/env python3
"""Read-only textbook LAB guide inventory: no ROS or simulator execution."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"(?<!!)\[[^\]\n]*\]\(([^)\n]+)\)")
FENCE = re.compile(r"^\s*" + re.escape(chr(96) * 3), re.MULTILINE)


def markdown_targets(text):
    """Return Markdown link paths only; code paths and external URLs are not L0 claims."""
    for match in LINK.finditer(text):
        value = match.group(1).strip().split(" ", 1)[0].strip("<>")
        if value.startswith(("https://", "http://", "mailto:", "#", "data:")):
            continue
        value = unquote(value.split("#", 1)[0].split("?", 1)[0])
        if value.lower().endswith(".md"):
            yield value


def audit_file(path, root):
    item = {"path": str(path.relative_to(root)), "status": "PASS", "issues": [], "warnings": [], "code_blocks": 0}
    if not path.is_file():
        item["issues"].append("Missing Markdown file")
    else:
        text = path.read_text(encoding="utf-8")
        for target in markdown_targets(text):
            resolved = (path.parent / target).resolve()
            if not resolved.is_relative_to(root.resolve()):
                item["issues"].append("Relative Markdown link leaves repository: " + target)
            elif not resolved.is_file():
                item["issues"].append("Broken Markdown link: " + target)
        fences = FENCE.findall(text)
        if len(fences) % 2:
            item["issues"].append("Unbalanced fenced code block")
        item["code_blocks"] = len(fences) // 2
        if path.name.startswith("LAB_") and not fences:
            item["warnings"].append("No fenced code block; check manual/conceptual lab")
    if item["issues"]:
        item["status"] = "FAIL"
    return item


def audit_chapter(chapter, root, spec):
    base = root / chapter
    readme = base / "README.md"
    guides = sorted((base / "docs").glob("LAB_*_GUIDE_KO.md"))
    if chapter == "Ch13":
        special = base / "docs" / "START_HERE_13_8_KO.md"
        if special.is_file():
            guides.append(special)
    files = [audit_file(p, root) for p in [readme, *guides]]
    problems = []
    if len(guides) < spec["minimum_guides"]:
        problems.append("Guide count " + str(len(guides)) + " below minimum " + str(spec["minimum_guides"]))
    for required in spec.get("required", []):
        if not (base / required).is_file():
            problems.append("Required guide missing: " + required)
    return {
        "chapter": chapter,
        "status": "FAIL" if problems or any(x["status"] == "FAIL" for x in files) else "PASS",
        "guide_count": len(guides),
        "inventory_issues": problems,
        "files": files,
        "runtime": "NOT_RUN",
    }


def export_report(data, output):
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    suite = ET.Element("testsuite", name="book-guide-preflight")
    cases = []
    for chapter in data["chapters"]:
        cases.append((chapter["chapter"] + " inventory", chapter["inventory_issues"]))
        for file in chapter["files"]:
            cases.append((file["path"], file["issues"]))
    for item in data["root_files"]:
        cases.append((item["path"], item["issues"]))
    for name, problems in cases:
        case = ET.SubElement(suite, "testcase", name=name, classname="book.preflight")
        if problems:
            ET.SubElement(case, "failure", message="; ".join(problems)).text = "\n".join(problems)
    suite.set("tests", str(len(cases)))
    suite.set("failures", str(sum(bool(x[1]) for x in cases)))
    suite.set("errors", "0")
    ET.ElementTree(suite).write(output / "junit.xml", encoding="utf-8", xml_declaration=True)
    lines = [
        "# Book LAB guide preflight",
        "",
        "Source: " + str(data["source_sha"]),
        "",
        "| Chapter | Guides | Document result | Runtime |",
        "|---|---:|---|---|",
    ]
    for ch in data["chapters"]:
        lines.append("| " + ch["chapter"] + " | " + str(ch["guide_count"]) + " | " + ch["status"] + " | NOT_RUN |")
    failures = [(name, problems) for name, problems in cases if problems]
    lines.append("")
    lines.append("Broken document checks: " + str(len(failures)))
    for name, issues in failures:
        lines.append("- " + name + ": " + "; ".join(issues))
    lines.extend(["", "This is a documentation audit only; no ROS2/Gazebo/MuJoCo runtime PASS is implied.", ""])
    (output / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapter", choices=["all"] + ["Ch%02d" % i for i in range(1, 14)], default="all")
    parser.add_argument("--output", type=Path, default=ROOT / "ci-results" / "docs")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    manifest = json.loads((root / "ci" / "manifest.json").read_text(encoding="utf-8"))
    names = list(manifest["chapters"]) if args.chapter == "all" else [args.chapter]
    chapters = [audit_chapter(name, root, manifest["chapters"][name]) for name in names]
    root_files = [audit_file(root / "README.md", root)] if args.chapter == "all" else []
    result = {
        "source_sha": os.environ.get("GITHUB_SHA", "LOCAL_UNCOMMITTED"),
        "level": "L0_DOCUMENT_ONLY",
        "chapter_selection": args.chapter,
        "status": "FAIL" if any(x["status"] == "FAIL" for x in chapters) or any(x["status"] == "FAIL" for x in root_files) else "PASS",
        "chapters": chapters, "root_files": root_files,
    }
    export_report(result, args.output)
    print((args.output / "SUMMARY.md").read_text(encoding="utf-8"))
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
