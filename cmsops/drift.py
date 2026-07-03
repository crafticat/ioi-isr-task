from __future__ import annotations
import io, os, sys, zipfile

def normalize_zip(zip_bytes: bytes) -> dict[str, bytes]:
    """Zip → {path: content}, order-independent (dict compare ignores order)."""
    out: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for name in z.namelist():
            if name.endswith("/"):
                continue
            out[name] = z.read(name)
    return out

def strip_top_dir(tree: dict[str, bytes]) -> dict[str, bytes]:
    """If every path shares one top-level directory (as italy_yaml exports do,
    packing a task under <taskname>/), strip it so the export tree aligns with
    the repo's task-relative paths. No-op when paths don't share one top dir.
    NOTE: byte-exact-serialization drift (re-zipped tests, key reordering) is a
    separate concern that must be validated against a real export when wiring live."""
    if not tree:
        return {}
    tops = {p.split("/", 1)[0] for p in tree}
    if len(tops) != 1 or not all("/" in p for p in tree):
        return dict(tree)
    return {p.split("/", 1)[1]: data for p, data in tree.items()}

def diff_trees(repo: dict[str, bytes], live: dict[str, bytes]) -> list[str]:
    """Return sorted paths that differ (added, removed, or changed)."""
    changed = set()
    for path in set(repo) | set(live):
        if repo.get(path) != live.get(path):
            changed.add(path)
    return sorted(changed)

def write_tree(tree: dict[str, bytes], dest_dir: str) -> None:
    for path, data in tree.items():
        full = os.path.join(dest_dir, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as fh:
            fh.write(data)

def main() -> int:
    """For each task in tasks/<dir> with a known CMS id, export live, diff, and
    if different, overwrite the working tree so drift.yml can open a PR."""
    from cmsops.client import CmsAdminClient
    from cmsops.config import Settings
    import json
    client = CmsAdminClient(Settings.from_env())
    if not os.path.exists("task_ids.json"):
        raise SystemExit(
            "task_ids.json not found: create it as a JSON object mapping each "
            "tasks/<dirname> to its CMS task id, e.g. {\"uchuva\": 12}")
    with open("task_ids.json") as fh:
        mapping = json.load(fh)   # {"<dirname>": <cms_task_id>}
    any_drift = False
    for dirname, task_id in mapping.items():
        live = strip_top_dir(normalize_zip(client.export_task(task_id)))
        repo_dir = os.path.join("tasks", dirname)
        repo = _read_tree(repo_dir)
        changed = diff_trees(repo, live)
        if changed:
            any_drift = True
            print(f"DRIFT {dirname}: {', '.join(changed)}")
            _clear_dir(repo_dir)
            write_tree(live, repo_dir)
    # GitHub disabled ::set-output in 2023 — write to $GITHUB_OUTPUT instead.
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as fh:
            fh.write(f"drift={'true' if any_drift else 'false'}\n")
    print(f"drift={'true' if any_drift else 'false'}")
    return 0

def _read_tree(root: str) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for base, _dirs, files in os.walk(root):
        for f in files:
            full = os.path.join(base, f)
            rel = os.path.relpath(full, root)
            with open(full, "rb") as fh:
                out[rel] = fh.read()
    return out

def _clear_dir(root: str) -> None:
    import shutil
    if os.path.isdir(root):
        shutil.rmtree(root)
    os.makedirs(root, exist_ok=True)

if __name__ == "__main__":
    sys.exit(main())
