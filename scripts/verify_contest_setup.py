#!/usr/bin/env python3
"""Idempotently create the verify contest + verifier user + participation.

Run INSIDE the devcms container with the CMS venv python (needs cms.db and a
reachable database). Prints the contest id as the LAST line of stdout so
callers can capture it:

    cid=$(/home/cmsuser/cms/bin/python /verify/scripts/verify_contest_setup.py | tail -1)

The contest mirrors the iloi-cms-task skill's setup recipe: infinite tokens,
C++17 enabled (cmsAddSubmission infers the language from the file extension
against this list).
"""
CONTEST_NAME = "verify"
USERNAME = "verifier"
PASSWORD = "verify"


def main() -> int:
    from cms.db import Contest, Participation, SessionGen, User
    from cmscommon.crypto import build_password

    with SessionGen() as s:
        contest = s.query(Contest).filter(Contest.name == CONTEST_NAME).first()
        if contest is None:
            contest = Contest(
                name=CONTEST_NAME,
                description="cmsops verify contest",
                allowed_localizations=["en", "he"],
                languages=["C++17 / g++"],
                token_mode="infinite",
                score_precision=2,
            )
            s.add(contest)
            s.flush()
        user = s.query(User).filter(User.username == USERNAME).first()
        if user is None:
            user = User(
                first_name="verify",
                last_name="bot",
                username=USERNAME,
                password=build_password(PASSWORD),
                email="verify@example.invalid",
            )
            s.add(user)
            s.flush()
        participation = (
            s.query(Participation)
            .filter(Participation.contest_id == contest.id,
                    Participation.user_id == user.id)
            .first()
        )
        if participation is None:
            s.add(Participation(contest=contest, user=user))
        s.commit()
        print(contest.id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
