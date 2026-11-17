#!/usr/bin/env python3
"""One-shot, allowlisted cleanup of proven merged PR branches.

Use only from trusted same-repository GitHub Actions with contents:write.
Never touches main, PR heads/bases still open, HOLD/backup, unmerged changes.
Each deletion checks PR merged, immutable HEAD SHA, latest main pin, and 404.
A successful dry-run only validates the proposed list, not remote deletion.
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPO = "silverbjin/Pysical_AI_ROS2"
CATEGORIES = {
    "CANDIDATE_DELETE_MERGED_HEAD_UNCHANGED",
    "CANDIDATE_DELETE_MAIN_ANCESTOR",
}


def candidate_list(data):
    if data["repository"] != REPO:
        raise ValueError("REPOSITORY_MISMATCH")
    if data["current_main_sha"] != "9431fb535ce7a51416c19c4395fb2ba3fabdad40":
        raise ValueError("UNEXPECTED_MAIN_SHA")
    if data["original_branch_count"] != 197:
        raise ValueError("UNEXPECTED_BRANCH_SNAPSHOT")
    candidates = [x for x in data["branches"] if x["cleanup"] in CATEGORIES]
    if len(candidates) != 54:
        raise ValueError("CLEANUP_COUNT_CHANGED")
    names = [x["name"] for x in candidates]
    if len(set(names)) != len(names):
        raise ValueError("DUPLICATE_CANDIDATE")
    for x in candidates:
        branch = x["name"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9/_-]*", branch):
            raise ValueError("UNSAFE_BRANCH_NAME")
        if (branch == "main" or branch.startswith(("hold/", "backup/",
                "diagnostic/", "experiment/")) or x["open_prs"]
                or x["dependent_open_prs"] or not x["merged_pr"]):
            raise ValueError("PROTECTED_BRANCH_IN_CANDIDATES: " + branch)
        if x["cleanup"] == "CANDIDATE_DELETE_MERGED_HEAD_UNCHANGED":
            if x["head_sha"] != x["merged_pr_head_sha"]:
                raise ValueError("MERGED_SHA_NOT_EQUAL")
        elif x["compare_to_main"]["ahead"] != 0:
            raise ValueError("NOT_ANCESTOR_OF_MAIN")
    return candidates


def api(method, relative, token, payload=None, missing_ok=False):
    req = Request(
        "https://api.github.com/repos/" + REPO + "/" + relative,
        data=(json.dumps(payload).encode("utf-8") if payload is not None else None),
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "book-branch-verified-prune/20261117",
        },
        method=method,
    )
    try:
        with urlopen(req, timeout=35) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        if missing_ok and exc.code == 404:
            return None
        error = exc.read(1000).decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {method} failed status={exc.code}: {error}")


def run(data, mode):
    candidates = candidate_list(data)
    result = {
        "scope": "VERIFIED_MERGED_MAIN_PR_BRANCH_DELETION",
        "snapshot_main_sha": data["current_main_sha"],
        "snapshot_branch_total": data["original_branch_count"],
        "mode": mode,
        "eligible_count": len(candidates),
        "deleted": [],
        "skipped": [],
        "failed": [],
        "dry_run": mode != "apply",
        "complete": False,
    }
    if mode != "apply":
        result["skipped"] = [
            {"name": x["name"], "reason": "DRY_RUN_NO_REMOTE_MUTATION"}
            for x in candidates
        ]
        result["complete"] = True
        return result

    if os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise RuntimeError("GITHUB_REPOSITORY_MISMATCH")
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        raise RuntimeError("NOT_TRUSTED_PULL_REQUEST_EVENT")
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    pull = event.get("pull_request", {})
    if (event.get("action") != "labeled"
        or event.get("label", {}).get("name") != "book-prune-merged-exact-once"
        or pull.get("head", {}).get("ref") != "audit/book-branch-lineage-prune-20261117"
        or pull.get("head", {}).get("repo", {}).get("full_name") != REPO):
        raise RuntimeError("TRUSTED_LABELED_PR_GATE_NOT_MET")
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_WRITE_TOKEN_MISSING")

    main = api("GET", "git/ref/heads/main", token)
    if main["object"]["sha"] != data["current_main_sha"]:
        raise RuntimeError("MAIN_MOVED_ABORT_WHOLE_BATCH")

    open_prs = api("GET", "pulls?state=open&per_page=100", token)
    if len(open_prs) >= 100:
        raise RuntimeError("OPEN_PR_LIST_PAGINATION_UNSAFE")
    protected = {p["head"]["ref"] for p in open_prs}
    protected.update(p["base"]["ref"] for p in open_prs)

    for x in candidates:
        branch = x["name"]
        try:
            if branch in protected:
                result["skipped"].append({"name": branch, "reason": "OPEN_PR_DEPENDENCY"})
                continue
            # Expected SHA is always from the initial read-only inventory;
            # if branch was edited, skip (never erase new work).
            refpath = "git/ref/heads/" + quote(branch, safe="/")
            current = api("GET", refpath, token, missing_ok=True)
            if current is None:
                result["skipped"].append({"name": branch, "reason": "ALREADY_ABSENT"})
                continue
            if current["object"]["sha"] != x["head_sha"]:
                result["skipped"].append({"name": branch, "reason": "BRANCH_HEAD_CHANGED"})
                continue
            pr = api("GET", f"pulls/{x['merged_pr']}", token)
            if (not pr.get("merged_at") or pr["head"]["ref"] != branch
                or pr["base"]["ref"] != "main"):
                result["skipped"].append({"name": branch, "reason": "MERGED_PR_CONTRACT_CHANGED"})
                continue
            if x["cleanup"] == "CANDIDATE_DELETE_MERGED_HEAD_UNCHANGED":
                if pr["head"]["sha"] != x["head_sha"]:
                    result["skipped"].append({"name": branch, "reason": "MERGED_PR_SHA_CHANGED"})
                    continue
            else:
                comp = api("GET", "compare/main..." + quote(x["head_sha"], safe=""), token)
                if comp.get("ahead_by") != 0:
                    result["skipped"].append({"name": branch, "reason": "NOT_MAIN_ANCESTOR"})
                    continue
            api("DELETE", "git/refs/heads/" + quote(branch, safe="/"), token)
            if api("GET", refpath, token, missing_ok=True) is not None:
                result["failed"].append({"name": branch, "reason": "DELETE_NO_404"})
                continue
            result["deleted"].append({
                "name": branch, "expected_sha": x["head_sha"],
                "merged_pr": x["merged_pr"],
                "remote_post_delete": "HTTP_404_VERIFIED",
            })
            print(f"BOOK_MERGED_BRANCH_DELETE_VERIFIED {branch} PR#{x['merged_pr']}", flush=True)
        except Exception as exc:
            result["failed"].append({"name": branch, "reason": str(exc)[:250]})
            print(f"BOOK_BRANCH_DELETE_FAILED name={branch} reason={type(exc).__name__}",flush=True)
        time.sleep(0.13)
    result["complete"] = not result["failed"] and (
        len(result["deleted"]) + len(result["skipped"]) == len(candidates)
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=["plan", "apply"], default="plan")
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = run(data, args.mode)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    if args.mode == "plan":
        print("BOOK_BRANCH_PRUNE_PLAN_PASS_ELIGIBLE_54_NO_MUTATION")
    else:
        print("BOOK_BRANCH_PRUNE_APPLY deleted=%d skipped=%d failed=%d" %
              (len(result["deleted"]), len(result["skipped"]), len(result["failed"])))
    if not result["complete"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
