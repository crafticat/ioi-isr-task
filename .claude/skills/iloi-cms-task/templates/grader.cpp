// Template grader.  Lives in both sol/ and att/ (contestants see the att/
// copy; CMS links the sol/ copy with the contestant's submission).
#include <cstdio>
#include <vector>
#include "TASKNAME.h"  // RENAME

int main() {
    int U, N;                            // RENAME / adjust per problem
    if (scanf("%d", &U) != 1) return 1;
    if (scanf("%d", &N) != 1) return 1;
    std::vector<long long> P(N);
    for (int i = 0; i < N; ++i) {
        if (scanf("%lld", &P[i]) != 1) return 1;
    }
    long long ans = TASKNAME(U, N, P);   // RENAME
    printf("%lld\n", ans);
    return 0;
}
