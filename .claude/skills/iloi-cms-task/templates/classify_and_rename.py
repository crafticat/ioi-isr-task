#!/usr/bin/env python3
"""Classify each generated test by which subtask validators it satisfies,
then re-lay-out tests under tests/ with regex-friendly codenames.

This enables subtask containment via the regex form of
score_type_parameters in task.yaml:

    [[0, ".*s.*"], [3, ".*a.*"], [4, ".*b.*"],
     [21, ".*c.*"], [35, ".*d.*"], [37, ".*e.*"]]

Each test goes into EVERY subtask whose constraints it satisfies, not
just the one its #ST: marker landed it in.

Letter convention (adjust SUBTASK_LETTER to fit your task):

    s  ->  subtask 0  (samples; 0 pts)
    a  ->  subtask 1
    b  ->  subtask 2
    c  ->  subtask 3
    d  ->  subtask 4
    e  ->  subtask 5  (full — every valid test)

A test with codename "017_bde" is in subtasks 2, 4, 5.

Run after gen/build_tests.py — see gen/build_tests.py for the chain.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INP_DIR = ROOT / "input"
OUT_DIR = ROOT / "output"
TESTS_DIR = ROOT / "tests"
VAL_DIR = ROOT / "validators"
BIN_DIR = ROOT / "gen" / "_validator_bins"
GEN_FILE = ROOT / "gen" / "GEN"

# Subtask index -> letter.  Subtask 0 is samples by convention.
SUBTASK_LETTER = {0: "s", 1: "a", 2: "b", 3: "c", 4: "d", 5: "e"}

CXX = os.environ.get("CXX", "g++")
CXXFLAGS = ["-std=c++17", "-O2", "-Wall", "-Wextra"]


def parse_gen_st0_indices() -> set[int]:
    """Return the indices of tests under the #ST: 0 block in GEN — these
    are the samples; force-label them with 's' regardless of validator_0."""
    samples: set[int] = set()
    idx = 0
    in_samples = False
    for line in GEN_FILE.read_text().splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#ST:"):
            in_samples = (int(s.split(":", 1)[1].strip()) == 0)
            continue
        if s.startswith("#") and not s.startswith("#COPY:"):
            continue
        if in_samples:
            samples.add(idx)
        idx += 1
    return samples


def compile_validators() -> dict[int, Path]:
    BIN_DIR.mkdir(exist_ok=True)
    bins: dict[int, Path] = {}
    for src in sorted(VAL_DIR.glob("validator_*.cpp")):
        idx = int("".join(c for c in src.stem if c.isdigit()))
        out = BIN_DIR / src.stem
        subprocess.run([CXX, *CXXFLAGS, str(src), "-o", str(out)], check=True)
        bins[idx] = out
    return bins


def classify(test_input: bytes, validator_bins: dict[int, Path]) -> str:
    """Return the letter string for this test (sorted, no 's')."""
    letters: list[str] = []
    for sub_idx in sorted(validator_bins):
        if sub_idx == 0:
            continue  # samples handled separately
        r = subprocess.run([str(validator_bins[sub_idx])],
                           input=test_input, capture_output=True)
        if r.returncode == 0:
            letters.append(SUBTASK_LETTER[sub_idx])
    return "".join(letters)


def main() -> int:
    print("compiling validators...")
    bins = compile_validators()
    samples = parse_gen_st0_indices()
    print(f"sample testcases: {sorted(samples)}")

    if TESTS_DIR.exists():
        shutil.rmtree(TESTS_DIR)
    TESTS_DIR.mkdir()

    inputs = sorted(INP_DIR.glob("input*.txt"),
                    key=lambda p: int(p.stem.removeprefix("input")))
    counts = {ltr: 0 for ltr in SUBTASK_LETTER.values()}

    for inp in inputs:
        i = int(inp.stem.removeprefix("input"))
        out = OUT_DIR / f"output{i}.txt"
        if not out.exists():
            sys.exit(f"missing output{i}.txt")
        data = inp.read_bytes()
        letters = classify(data, bins)
        if i in samples:
            letters = "s" + letters
        codename = f"{i:03d}_{letters or 'none'}"
        for ltr in letters:
            counts[ltr] += 1
        (TESTS_DIR / f"input.{codename}").write_bytes(data)
        shutil.copy(out, TESTS_DIR / f"output.{codename}")

    print(f"\nlaid out {len(inputs)} tests under tests/")
    print("per-subtask membership totals:")
    for sub_idx in sorted(SUBTASK_LETTER):
        ltr = SUBTASK_LETTER[sub_idx]
        print(f"  subtask {sub_idx} ('{ltr}'): {counts[ltr]:>4d} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
