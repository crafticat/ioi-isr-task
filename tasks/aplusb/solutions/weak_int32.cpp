// Deliberately weak solution: stores A and B in 32-bit ints.
// On subtask 2 the inputs exceed INT_MAX, operator>> sets failbit and stores 0
// (well-defined since C++11), so it prints a wrong value there. Subtask 1
// values fit in int, so it stays correct on ST1. No UB anywhere.
#include <iostream>

int main() {
    int a = 0, b = 0;
    std::cin >> a >> b;
    std::cout << a + b << std::endl;
    return 0;
}
