# Verification scripts and patterns

Three layers of verification developed for the Uchuva task. Adapt to your
problem; the contracts are the same.

## Layer 1 — brute force (ground truth on tiny inputs)

`_verify/brute.cpp` — exhaustive 2^T sign-mask enumerator capped at T ≤ 22.

```cpp
// Reads: U N P[0..N-1]
// Returns smallest T with some signed sum = -U, or -2 if undecided within CAP.
for (int T = 1; T <= CAP; ++T) {
    for (long long mask = 0; mask < (1LL << T); ++mask) {
        long long cur = U;
        for (int i = 0; i < T; ++i) {
            long long p = P[i % N];
            if (mask & (1LL << i)) cur -= p; else cur += p;
        }
        if (cur == 0) { printf("%d\n", T); return 0; }
    }
}
puts("-2");
```

Use with random small inputs (N ≤ 4, P[i] small, U ≤ 30).

## Layer 2 — independent algorithm (medium inputs)

`_verify/dp_ref.cpp` — classic subset-sum DP. **Different algorithm than the
model's carry trick**, so catches algorithmic bugs, not just impl bugs.

```cpp
// reach[v] = is v reachable as a subset sum of seen P's?
// At each new T, update reach[] for the new p, then check if (S - U) / 2
// is in reach[].
vector<char> reach(S_cap + 1, 0); reach[0] = 1;
for (int T = 1; T <= T_cap; ++T) {
    long long p = P[(T-1) % N];
    S += p;
    if (S > S_cap) { puts("-2"); return 0; }
    for (long long v = S; v >= p; --v)
        if (reach[v - p]) reach[v] = 1;
    if (S >= U && ((S - U) & 1) == 0) {
        long long V = (S - U) / 2;
        if (V <= S_cap && reach[V]) { printf("%d\n", T); return 0; }
    }
}
```

Returns "-2" when S exceeds budget or no solution found in T_cap iterations.

## Layer 3 — structural verifier (closed forms for tests beyond DP)

`_verify/structural.py` — for each generator mode (`n1_only`, `subtract_only`,
`path1big`), implement a closed-form answer derived from problem math, then
diff against the model.

```python
def predict_path1big(U, k):
    # P = [1, 2^k]; want signed_sum = -U.
    # x in [-c_0, c_0], y in [-c_M, c_M], x+y*M = -U.
    # iterate small y range, find smallest T.
    ...
```

## Stress test driver

`_verify/stress.py` — runs N_TRIALS random inputs through model + brute + DP,
flags any case where they disagree on a definite (non-(-2)) answer:

```python
candidates = {model_ans, brute_ans, dp_ans} - {"-2"}
if len(candidates) > 1:
    print(f"MISMATCH: model={model_ans} brute={brute_ans} dp={dp_ans}")
```

## Per-test driver

`_verify/check_testset.py` — walks every `input/*.txt` and verifies the
model's expected `output/*.txt`:

- If T_min ≤ DP_T_CAP_HARD: run DP at T_target=T_min; must succeed at
  T = T_min and fail at T = T_min - 1.
- If model says -1: run DP up to a generous cap; must also not find a
  solution.
- Else: skip + count as "DP can't decide".

Combined coverage on Uchuva: 72/142 DP-verified positive + 27/142
-1-consistent + 43/142 structural-verified. Zero mismatches.

## When to be paranoid

- Whenever you change the model after the testset is generated. The
  outputs in `output/` are stale until you re-run `gen/build_tests.py`,
  and even after, the model's bugs become the testset's bugs. Run all
  three verification layers after every model change.

- Whenever you change K_max / search bound / time-limit-influenced
  truncation. These often paper over algorithmic incompleteness on
  pathological inputs. Re-derive at U_max.

- Whenever an `expected_score_min/max` declaration changes. Re-run
  `gen/judge.py --verify-all`.
