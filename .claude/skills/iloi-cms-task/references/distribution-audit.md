# Per-subtask distribution audit (must run BEFORE red-teaming)

**Lesson learned the hard way on Uchuva**: red-team agents that
enumerate attacks miss *calibration* bugs in the testset. A subtask
"T_min ≤ 1000" with most tests at T_min < 100 is wide open to a
`brute_force_100` heuristic, even if no attacker ever tries cap=100.

## The pattern

Every subtask whose constraint is a NUMERICAL bound (`T_min ≤ B`,
`N ≤ B`, `U ≤ B`, etc.) should have its tests CLUSTERED near the
bound, not at the low end. Otherwise the bound is decorative — a
contestant whose algorithm is `O(any number < B)` passes for free.

## The audit script (drop into _verify/audit_distribution.py)

```python
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
# For each subtask, list (codename, T_min) and bucket by decade-of-T_min
for letter, name, bound in [
    ('d', 'ST4 (T_min<=1000)', 1000),
    # add more subtasks here
]:
    buckets = {}
    for inp in sorted((ROOT/'tests').glob('input.*')):
        codename = inp.name[len('input.'):]
        suffix = codename.split('_')[-1]
        if letter not in suffix: continue
        T = (ROOT/'tests'/f'output.{codename}').read_text().strip()
        if T == '-1':
            buckets.setdefault('-1', 0); buckets['-1'] += 1; continue
        Tn = int(T)
        # Bucket by powers of 10
        k = max(1, len(str(Tn)))
        bucket = f"10^{k-1}..10^{k}"
        buckets.setdefault(bucket, 0); buckets[bucket] += 1
    print(f"\n{name}:")
    for k in sorted(buckets): print(f"  {k:>14}: {buckets[k]}")
```

Run, eyeball. If any bucket near the constraint bound has < 10% of
total, you have calibration debt.

## When the audit reveals weak distribution

Don't just add adversarial tests randomly — construct inputs whose
T_min provably lands in the underserved bucket. For Uchuva path1big
`P=[1, 2^k]`, `T_min ≈ 2·max(|x|, |y|)` where `x + y·2^k = -U`. To
target T_min ≈ 800, pick `k=10`, `y=-1`, want `|x| ≈ 400` ⇒
`U = 2^k - 400 = 624`. Sweep U around that and ask the model for
T_min until you cover every 50-bucket from 500 to 1000.

Example sweep script: see Uchuva's `_verify/find_st4_hard.py`.

## Where this fits in the workflow

Insert BEFORE Phase 10b (red-teaming). Sequence:

1. Generate tests + classify_and_rename.
2. **Run distribution audit per subtask.** If any subtask has weak
   distribution → construct adversarial tests to fill the gap.
3. Iterate until distributions look OK.
4. THEN dispatch the red-team agent (it's good at finding bugs in
   algorithms but bad at finding bugs in the testset itself).

This is symmetric advice to the verification gauntlet: model bugs
are caught by *cross-checking the model*; testset calibration bugs
are caught by *cross-checking the testset's coverage of its own
stated constraints*. Different audits, both required.
