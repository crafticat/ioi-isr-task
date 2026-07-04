// Template validators/validator_<N>.cpp.  CMS compiles in isolate at import
// time and runs once per testcase with stdin = input.txt.  Exit 0 = pass,
// non-zero (with stderr message) = fail.
//
// Drop subtask-specific assertions in main().  For "structural" subtasks
// (subtract-only suffices, T_min<=K achievable, etc), re-implement the
// relevant feasibility check directly here so it's an independent witness
// of the testset's correctness.
//
// CARRY_LIMIT pitfall: never let `(V >> e)` reach e>=64 on signed long long.
// For T<=1000 (subtask 4 envelope), V<=2^50 so CARRY_LIMIT=62 is safe.
#include <cstdarg>
#include <cstdio>
#include <cstdlib>

[[noreturn]] static void die(const char* fmt, ...) {
    std::va_list a; va_start(a, fmt);
    std::vfprintf(stderr, fmt, a);
    std::fprintf(stderr, "\n");
    va_end(a);
    std::exit(1);
}

int main() {
    long long U;
    int N;
    if (std::scanf("%lld", &U) != 1) die("could not read U");
    if (U < 1 || U > 1000000000LL)   die("U=%lld out of range", U);
    if (std::scanf("%d", &N) != 1)   die("could not read N");
    if (N < 1 || N > 100000)         die("N=%d out of range", N);

    for (int i = 0; i < N; ++i) {
        long long p;
        if (std::scanf("%lld", &p) != 1) die("could not read P[%d]", i);
        if (p < 1 || p > (1LL << 40))    die("P[%d]=%lld out of range", i, p);
        if (p & (p - 1))                 die("P[%d]=%lld not a power of 2", i, p);
    }
    int c;
    while ((c = std::getchar()) != EOF)
        if (c != ' ' && c != '\n' && c != '\t' && c != '\r')
            die("unexpected trailing character '%c'", c);

    // SUBTASK-SPECIFIC ASSERTIONS BELOW
    // e.g. if (N != 1) die("subtask requires N=1");
    return 0;
}
