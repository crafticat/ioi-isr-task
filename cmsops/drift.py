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
    mapping = json.load(open("task_ids.json"))   # {"<dirname>": <cms_task_id>}
    any_drift = False
    for dirname, task_id in mapping.items():
        live = normalize_zip(client.export_task(task_id))
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
            out[rel] = open(full, "rb").read()
    return out

def _clear_dir(root: str) -> None:
    import shutil
    if os.path.isdir(root):
        shutil.rmtree(root)
    os.makedirs(root, exist_ok=True)

if __name__ == "__main__":
    sys.exit(main())
