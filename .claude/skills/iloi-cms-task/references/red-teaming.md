# Red-teaming an ILOI testset

Before declaring the testset done, dispatch an adversarial agent.  It
writes 8-12 buggy/heuristic solutions, scores them via the local judge,
and reports each as `ATTACK <name>: expected_max actual which_subtask`.

## Threat model (set this carefully)

The red-team agent's POWER must match a realistic contestant. Get
this wrong and findings are either fake (too much access) or miss
real exploits (too little).

A realistic ILOI contestant has:
- The problem statement.
- Subtask weights and constraints.
- Sample tests (the public-by-name ones).
- Per-test verdict from CMS after they submit.
- Worst-case: a leaked generator source (`gen/generator.cpp` +
  `gen/GEN`).

A realistic contestant does NOT have:
- Test input bytes (CMS hides them — `public_testcases: "all"` only
  controls verdict visibility, not byte exposure).
- Test output bytes (likewise).
- The model solution source.

**If you give the agent filesystem access to `tests/` or
`output/`, you're testing a fake threat.** Findings like
"hardcoded-table attack scores 100/100" become meaningless — no
real contestant can run that attack.

## Dispatching the agent

```
Agent({
  description: "Red-team <task> testset",
  subagent_type: "general-purpose",
  prompt: """
  You are red-teaming the <task> at <path>.  Read sol/<task>.cpp and
  solutions/*.cpp (existing reference solutions and their declared
  expected_score_min/max in task.yaml).  Use gen/judge.py to score
  candidates.  Write at least 8 DIFFERENT buggy solutions targeting:

    - Heuristics: greedies (largest first, smallest first, alternating)
    - Wrong subset-sum impls (carry direction flipped, parity ignored)
    - Wrong bounds (int instead of long long, off-by-one)
    - Wrong subtract-only (forgets cyclic wrap)
    - Partial-credit floor exploits (divisibility + return-1 fallback)
    - Slow correct algos (O(T) iteration without cap)
    - Multi-special-case stacks (N=1 closed + N=2 full + brute T<=K)
    - Almost-correct (e.g. correct only when min(P) divides U trivially)

  For each solution scoring MORE than it should, write
    ATTACK <name>: <expected_max> <actual> <subtask_id>

  Recommend new GEN-file lines per leak using existing generator modes.
  Do NOT fix the testset; report only.  Under 800 words.
  """,
  run_in_background: true
})
```

## Standard attack classes (for the agent to enumerate)

1. **greedy_subtract**: `for (; U > 0; U -= P[(ans++) % N]); return U ? -1 : ans;`
   — should TLE on subtract-only with T_min near U_max.

2. **greedy_largest_first**: at each turn pick sign that gets you closer
   to 0 — overshoots on N=2 / sparse cycles.

3. **divisibility_then_one**: `if (U % minP == 0) return 1; else return -1;`
   — the literal 15%-floor exploit.

4. **subtract_only_pure** / **subtract_only_fallback**: pure and +fallback.

5. **n1_only / n2_only / n1_n2_only**: special-case the small-N
   subtasks; -1 elsewhere (no fallback) or fallback to qualify for 15%.

6. **brute_force_K**: T-bounded bit-carry brute force (K = 1000, 200k).

7. **int_overflow**: model with `int` instead of `long long`.

8. **feasibility_no_carry**: subset sum without the carry-propagation
   step in the bit sweep.

9. **wrong_kmax**: model with K_max tightened to Un/2 — should fail on
   path1big with T_min ≈ 2·U.

10. **multi_special_stack**: N=1 closed + N=2 full + subtract-only +
    brute T≤K + fallback (the "stitcher" that earns multiple subtasks
    legitimately).

## Classifying the agent's report

This is the most important part — **most findings are NOT leaks**.
Three categories:

### A. Real leaks — add adversarial GEN lines

The attacker has a wrong/incomplete algorithm yet passes a subtask.
Example: greedy_subtract passing ST2 when T_min should TLE it.

**Action:** add tests that defeat the attacker's class of mistake.

### B. Hardware artifacts — verify on contest hardware

Solution passes locally but would TLE on a typical 3 GHz Xeon contest
server (M-series Macs run tight C++ loops at ~3× contest hardware).

**How to verify:** temporarily lower the dataset's time_limit to
0.2-0.5s, resubmit, see if it TLEs there. If yes → trust contest
hardware; if no → genuine leak, treat as category A.

### C. Legitimate per-subtask scoring — DO NOT fix

A stitched-together solver that correctly implements one algorithm per
subtask (N=1 closed + N=2 full + brute T≤K + fallback) earns those
subtasks fully.  The agent flags this as a "leak scoring 65-70".

**It isn't a leak.**  IOI/ILOI subtasks reward per-subtask algorithmic
capability.  A contestant who actually implemented a correct N=2 solver
deserves ST3 points regardless of whether they have the full algo.
The full subtask (ST5) is worth more than the rest combined, so the
stitched-together solver can't beat the intended solution overall.

**If you "fix" this by adding tests, you break subtask containment.**

## After the agent reports

**Iteration is mandatory** — every fix must be re-verified by the
agent or the next-round agent could find a new exploit class that
the fix enabled.  The pattern:

1. Add adversarial GEN lines / change parameters / fix model for each
   category-A leak.
2. Re-run `python3 gen/build_tests.py` (it also runs
   `classify_and_rename.py` automatically).
3. Re-import into CMS (`cmsImportTask --update`).
4. Re-verify reference solutions still match declared expected scores
   (catches model regressions immediately).
5. Re-submit the exploit attack(s) the agent found.  Confirm the
   score now drops to the expected ceiling.  **Many "fixes" are
   incomplete** — e.g. adding mixed_required with T=5000 doesn't
   force T_min > 1000 because the model finds shorter paths; need
   to cherry-pick seeds + verify offline that T_min comes back
   above the threshold.
6. **Re-dispatch the red-team agent** with an updated prompt that
   summarises the fix you applied and asks "find any NEW exploit
   class that this fix enables, or confirm the ceiling holds."  Use
   the same agent's `agentId` via SendMessage so it has context.
7. Iterate steps 1-6 until the agent reports only category B + C
   findings AND can't find anything better than the documented
   `cheap_combo` ceiling.

**Common iteration mistakes:**
- Adding tests blindly without verifying T_min/N/U lands where you
  need it (run model offline + check before committing GEN line).
- Forgetting step 4 — a fix that breaks a reference solution's
  declared score is itself a bug.
- Stopping after one iteration — most fixes incidentally enable
  new attack classes (e.g. adding mid-N tests reveals that small-N
  patterns become more profitable proportionally).
- Not searching offline for seeds that produce the *desired
  property*; relying on the construction parameter as a proxy.

## Practical floors

- **15% partial-credit rule**: any "sane" solver gets `0.15 × 100 = 15`
  pts free.  By problem-statement design, not a bug.
- **Subtask 1 (N=1)**: any solver that handles N=1 correctly gets the
  ST1 points.  Often 3-5 pts is appropriate.
- **Stitched multi-subtask**: with proper containment, a solver
  earning ST1+ST2+ST3+ST4 fully + 15% on ST5 reaches `3+4+21+35+5.55 ≈
  68.55` on a 100-pt task.  This is the design ceiling for partial
  solvers; the full subtask must be worth > 100 - that to prevent
  full-credit via stitching.
