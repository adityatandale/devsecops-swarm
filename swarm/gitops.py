"""Authenticated pull-request submission with GitPython + GitHub REST API."""
from pathlib import Path

import requests

from .config import BASE_BRANCH, GITHUB_REPO, GITHUB_TOKEN, RUNS_DIR


def build_pr_body(state: dict) -> str:
    inc, patch, res = state["incident"], state["patch"], state["test_result"]
    return (
        f"## 🤖 Automated fix for incident `{inc['id']}`\n\n"
        f"**Error:** `{inc['exception_type']}: {inc['exception_message']}`\n"
        f"**Service:** {inc['service']}\n\n"
        f"### Root cause & fix\n{patch['explanation']}\n\n"
        f"### Validation\n- Tests passed in ephemeral Docker sandbox ({res.get('mode')})\n"
        f"- Security scan (bandit, HIGH): {'clean' if res.get('security_passed') else 'findings'}\n"
        f"- Attempts needed: {state.get('attempt')}\n\n"
        f"### Diff\n```diff\n{patch['diff']}\n```\n\n"
        "> Generated autonomously by the Self-Healing DevSecOps swarm. **Human review required before merge.**"
    )


def submit_pr(state: dict, dry_run: bool = True) -> dict:
    inc, patch, target = state["incident"], state["patch"], state["target"]
    branch = f"autofix/{inc['id']}"
    title = f"fix: {inc['exception_type']} in {target['function']}()"
    body = build_pr_body(state)

    if dry_run:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        patch_file = RUNS_DIR / f"{inc['id']}.patch"
        patch_file.write_text(patch["diff"])
        (RUNS_DIR / f"{inc['id']}_PR.md").write_text(f"# {title}\n\n{body}")
        return {"dry_run": True, "branch": branch, "title": title, "patch_file": str(patch_file)}

    if not (GITHUB_TOKEN and GITHUB_REPO):
        raise RuntimeError("GITHUB_TOKEN and GITHUB_REPO must be set when DRY_RUN_PR=false")

    from git import Actor, Repo

    repo = Repo(state["repo"])
    original_branch = repo.active_branch.name
    actor = Actor("Self-Healing Swarm", "swarm@users.noreply.github.com")
    try:
        repo.git.checkout("-b", branch)
        Path(state["repo"], target["file"]).write_text(patch["patched_text"], encoding="utf-8")
        repo.index.add([target["file"]])
        repo.index.commit(f"{title}\n\nIncident {inc['id']}: {inc['signature']}", author=actor, committer=actor)
        push_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
        try:
            repo.git.push(push_url, f"{branch}:{branch}")
        except Exception as exc:
            raise RuntimeError(str(exc).replace(GITHUB_TOKEN, "***")) from None
    finally:
        repo.git.checkout(original_branch)

    resp = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/pulls",
        headers={"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"},
        json={"title": title, "head": branch, "base": BASE_BRANCH, "body": body},
        timeout=30,
    )
    resp.raise_for_status()
    return {"dry_run": False, "branch": branch, "title": title, "url": resp.json()["html_url"]}
