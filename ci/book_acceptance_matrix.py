#!/usr/bin/env python3
"""Book #118 evidence-led inventory. No ROS / Gazebo / MuJoCo execution.

An L0 guide check, a section-scoped runtime PASS and a complete textbook LAB
are three distinct things. Do not infer section acceptance from successful CI.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path
import re
import sys

CHAPTER_SECTIONS = {1: 7, 2: 8, 3: 9, 4: 7, 5: 6, 6: 7,
                    7: 7, 8: 8, 9: 8, 10: 8, 11: 7, 12: 8, 13: 8}
# The book has 98 numbered sections, but several Ch13 main guides use
# descriptive suffixes rather than the original generic LAB_13_N_GUIDE name.
# These are ALIASES for numbered sections, not additional runtime labs.
CH13_MAIN_GUIDE_ALIASES = {
    6: "LAB_13_6_REUSE_GUIDE_KO.md",
    7: "LAB_13_7_BT_GUIDE_KO.md",
    8: "START_HERE_13_8_KO.md",
}
ALLOWED = {"SCOPED_PASS", "FAIL", "BLOCKED", "HOLD",
           "EVIDENCE_REVIEW_REQUIRED", "FILE_MISSING"}
COLUMNS = ("chapter", "section", "primary_guide", "exists", "status",
           "ci_run", "artifact_id", "issue", "note", "acceptance_level")


def section_records(root, registry):
    records = registry["records"]
    expected = {f"Ch{chapter:02d}/{chapter}.{section}"
                for chapter, n in CHAPTER_SECTIONS.items()
                for section in range(1, n + 1)}
    unknown = sorted(set(records) - expected)
    if unknown:
        raise ValueError(f"unrecognized section evidence keys: {unknown}")
    result = []
    for chapter, n in CHAPTER_SECTIONS.items():
        chapter_dir = root / f"Ch{chapter:02d}"
        for section in range(1, n + 1):
            key = f"Ch{chapter:02d}/{chapter}.{section}"
            name = (CH13_MAIN_GUIDE_ALIASES.get(section)
                    if chapter == 13 and section in CH13_MAIN_GUIDE_ALIASES
                    else f"LAB_{chapter}_{section}_GUIDE_KO.md")
            doc = chapter_dir / "docs" / name
            evidence = records.get(key, {})
            status = evidence.get("status", "EVIDENCE_REVIEW_REQUIRED")
            if status not in ALLOWED:
                raise ValueError("unsupported state " + status)
            if not doc.is_file():
                status = "FILE_MISSING"
            row = {
                "chapter": f"Ch{chapter:02d}",
                "section": f"{chapter}.{section}",
                "primary_guide": str(doc.relative_to(root)),
                "exists": doc.is_file(),
                "status": status,
                "ci_run": evidence.get("ci_run") or "",
                "artifact_id": evidence.get("artifact_id") or "",
                "issue": evidence.get("issue") or "",
                "note": evidence.get("note") or
                        "이 절을 PASS로 판정할 실측 증거 연결 미완료; 기존 보고서 확인 필요",
                "acceptance_level": "SCOPED_ONLY" if status == "SCOPED_PASS" else
                                    "UNACCEPTED",
            }
            if status == "SCOPED_PASS" and not (row["ci_run"] or row["note"]):
                raise ValueError(f"source evidence missing for {key}")
            result.append(row)
    return result


def supporting_guides(root, rows):
    primary = {r["primary_guide"] for r in rows}
    docs = []
    for ch in range(1, 14):
        docs.extend((root / f"Ch{ch:02d}" / "docs").glob("LAB_*_GUIDE_KO.md"))
    # Special published Ch13 basic walkthrough, not a ninth numbered section.
    docs.append(root / "Ch13/docs/START_HERE_13_8_KO.md")
    unique = sorted({str(p.relative_to(root)): p for p in docs}.items())
    extra = [
        {"path": rel, "exists": path.is_file(), "classification": "SUPPLEMENTAL_GUIDE_NOT_INDEPENDENT_SECTION",
         "section_covered": ("13.5" if "13_5_REUSE" in rel else
                             "13.6" if "13_6_REUSE" in rel else
                             "13.8" if "START_HERE_13_8" in rel or "13_8_SYSTEM_VALIDATION" in rel else "UNMAPPED")}
        for rel, path in unique if rel not in primary
    ]
    return len(unique), extra


def audit(root, registry):
    rows = section_records(root, registry)
    doc_count, supplementals = supporting_guides(root, rows)
    counter = Counter(r["status"] for r in rows)
    missing_ci = [r["section"] for r in rows if
                  r["status"] == "SCOPED_PASS" and not r["ci_run"]]
    inventory_gaps = [r["section"] for r in rows if not r["exists"]]
    target = registry["acceptance_target_from_issue_118"]
    # Unlike a CI job, a book-closeout verdict cannot be PASS with any
    # scoped-only evidence, open HOLD, missing guide, or unverified section.
    return {
        "source_baseline_sha": registry["baseline_main_sha"],
        "scope": "EVIDENCE_INVENTORY_ONLY_NO_RUNTIME_EXECUTION",
        "target_from_issue_118": target,
        "numbered_sections": len(rows),
        "numbered_guide_files_present": sum(bool(r["exists"]) for r in rows),
        "unique_guide_documents_including_supporting": doc_count,
        "supplemental_guides": supplementals,
        "target_doc_count_equal": doc_count == target,
        "section_status_counts": dict(counter),
        "missing_guide_sections": inventory_gaps,
        "scoped_pass_missing_explicit_ci": missing_ci,
        "overall_101_lab_execution_accepted": False,
        "overall_verdict": "NOT_READY_FOR_FULL_RUNTIME_ACCEPTANCE",
        "ch10_hold": all(r["status"] == "HOLD" for r in rows if r["chapter"] == "Ch10"),
        "ch08_original_ppo_performance": "0_OF_10_FAIL",
        "ch11_original_save_map_service": "FAIL_255",
        "ch07_original_full_pick_place": "BLOCKED",
        "rows": rows,
    }


def write_report(data, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / "acceptance_matrix.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (out / "acceptance_matrix.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(data["rows"])
    lines = [
        "# 101 LAB evidence reconciliation (L0 inventory, not runtime)",
        "",
        f"- Baseline main: `{data['source_baseline_sha']}`",
        f"- Target (#118): {data['target_from_issue_118']} guide documents",
        f"- Numbered sections: {data['numbered_sections']} (primary LAB files present: {data['numbered_guide_files_present']})",
        f"- Distinct LAB/special guide documents: {data['unique_guide_documents_including_supporting']}",
        f"- Evidence/classification counts: {data['section_status_counts']}",
        f"- Explicit section CI links pending: {len(data['scoped_pass_missing_explicit_ci'])}",
        f"- Numbered LAB primary files not found at canonical paths: {len(data['missing_guide_sections'])} — {data['missing_guide_sections']}",
        "- **Overall runtime acceptance: NOT_READY**. SCOPED_PASS != complete section PASS.",
        "- **Ch10 #123: HOLD. No Ch10 runtime execution.**",
        "- Ch07 7.7 BLOCKED, Ch08 8.7 original PPO goal 0/10 FAIL, Ch11 save_map service FAIL.",
        "",
        "## Supplemental guide documents (not extra numbered sections)",
        "",
    ]
    for v in data["supplemental_guides"]:
        lines.append(f"- `{v['path']}`: maps to §{v['section_covered']}, exists={v['exists']}")
    lines.extend(["", "## Chapters and measured coverage", "",
                  "| Chapter | Sections | SCOPED_PASS | FAIL | BLOCKED | HOLD | Evidence unlinked |",
                  "|---|---:|---:|---:|---:|---:|---:|"])
    for ch in range(1,14):
        rr = [r for r in data["rows"] if r["chapter"] == f"Ch{ch:02d}"]
        cc = Counter(r["status"] for r in rr)
        lines.append(
            f"| Ch{ch:02d} | {len(rr)} | {cc['SCOPED_PASS']} | {cc['FAIL']} | "
            f"{cc['BLOCKED']} | {cc['HOLD']} | "
            f"{cc['EVIDENCE_REVIEW_REQUIRED']+cc['FILE_MISSING']} |")
    lines.extend(["",
      "## Next closure",
      "",
      "1. Link raw CI / Artifact for sections tagged EVIDENCE_REVIEW_REQUIRED and accepted-without-CI claims; **no re-running previous successes**.",
      "2. Finish Ch07 §7.7 only with real sensor→3D target→MoveIt→physical object pose evidence; otherwise publish as BLOCKED/advanced project.",
      "3. Ch08 original PPO performance FAIL remains unless a separately named new trained policy reaches stated held-out success criterion.",
      "4. Ch11 use separately proven official Nav2 CLI; keep upstream original SaveMap service FAIL/known limitation.",
      "5. Compare Ch12 §12.4–12.8 and Ch13 basic versus advanced against existing independent artifact, not guide presence.",
      "6. Scope manual GUI/WSL2 as a separate owner acceptance; Ch10 remains HOLD.",
      "",
      "No source code or model is evaluated by this inventory script.",
      "",
    ])
    (out / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--manifest", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    root = a.root.resolve()
    manifest = a.manifest or root / "ci/book_acceptance_evidence.json"
    output = a.output or root / "ci-results/book-101-matrix"
    registry = json.loads(manifest.read_text(encoding="utf-8"))
    data = audit(root, registry)
    write_report(data, output)
    print((output / "SUMMARY.md").read_text(encoding="utf-8"))
    # A valid audit may discover that not all textbook labs are accepted.
    # This exit code is ONLY for a correctly generated evidence inventory.
    return 0 if data["ch10_hold"] else 2


if __name__ == "__main__":
    sys.exit(main())
