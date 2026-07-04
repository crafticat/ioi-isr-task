// Template managers/checker.cpp — CMS comparator interface.
// Filename "checker" inside managers/ flips output_eval to "comparator".
//
//   argv[1] = input file
//   argv[2] = expected output
//   argv[3] = contestant output
//   stdout  = a single number in [0.0, 1.0]
//   stderr  = optional message shown to the contestant as the outcome text
//
// Combined with GroupMin: per-subtask score = min over tests * subtask points.
// Use a 0.15 outcome to implement the common 15%-partial-credit rule.
//
// IMPORTANT — feedback message convention. The stderr line becomes the
// contestant-facing outcome. Emit a `translate:<key>` TOKEN, not free English,
// so the CMS localizes it (the ILOI CMS renders `translate:success` etc. in the
// contestant's language). The three canonical keys are:
//     translate:success   (full credit)
//     translate:wrong     (no credit)
//     translate:partial   (partial credit)
// Free-text English here ships an un-localized, contest-inconsistent message —
// the production CMS import expects the tokens. (Discovered when the ILOI team
// re-exported Uchuva: every stderr string had been rewritten to a translate key.)
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>

static std::string trim(std::string s) {
    while (!s.empty() && (s.back()=='\n'||s.back()=='\r'||s.back()==' '||s.back()=='\t')) s.pop_back();
    size_t i = 0;
    while (i < s.size() && (s[i]==' '||s[i]=='\t'||s[i]=='\n'||s[i]=='\r')) ++i;
    return s.substr(i);
}
static std::string slurp(const char* p) {
    std::ifstream f(p); std::stringstream ss; ss << f.rdbuf();
    return trim(ss.str());
}

int main(int argc, char* argv[]) {
    if (argc < 4) { std::printf("0.0\n"); return 0; }
    std::string expected = slurp(argv[2]);
    std::string actual   = slurp(argv[3]);

    if (expected == "-1") {
        if (actual == "-1") { std::printf("1.0\n"); std::fprintf(stderr,"translate:success\n"); }
        else                { std::printf("0.0\n"); std::fprintf(stderr,"translate:wrong\n"); }
    } else {
        if (actual == expected)      { std::printf("1.0\n");  std::fprintf(stderr,"translate:success\n"); }
        else if (actual == "-1")     { std::printf("0.0\n");  std::fprintf(stderr,"translate:wrong\n"); }
        else if (!actual.empty())    { std::printf("0.15\n"); std::fprintf(stderr,"translate:partial\n"); }
        else                         { std::printf("0.0\n");  std::fprintf(stderr,"translate:wrong\n"); }
    }
    return 0;
}
