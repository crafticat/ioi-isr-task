// Model solution: 64-bit everywhere, correct on all subtasks.
#include <cstdio>

int main() {
    long long a, b;
    if (scanf("%lld %lld", &a, &b) != 2)
        return 1;
    printf("%lld\n", a + b);
    return 0;
}
