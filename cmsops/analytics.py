from __future__ import annotations

def parse_ranking_history(raw: list) -> list[dict]:
    """`.../combined_ranking/history` JSON = [user_id, task_id, time, score]
    (strings for the ids). Normalize to typed dict rows."""
    rows = []
    for entry in raw:
        uid, tid, t, score = entry
        rows.append({"user_id": int(uid), "task_id": int(tid),
                     "time": int(t), "score": float(score)})
    return rows

def users_with_full_score(rows: list[dict], task_id: int, full: float) -> list[int]:
    return sorted({r["user_id"] for r in rows
                   if r["task_id"] == task_id and r["score"] >= full})

def fetch_ranking_history(client, training_program_id: int) -> list[dict]:
    """GET the training-program ranking history via the read-only client."""
    client._ensure_login()
    resp = client.session.get(
        client._url(f"/training_program/{training_program_id}/combined_ranking/history"),
        timeout=120)
    resp.raise_for_status()
    return parse_ranking_history(resp.json())
