// Test fixture: minimal C file with a simple buffer overflow vulnerability
// Used as the first test case for parser integration tests.

int vulnerable_copy(char *src) {
    char buf[10];
    // CWE-121: Stack-based Buffer Overflow
    strcpy(buf, src);  // No bounds check
    return 0;
}

int safe_copy(char *src, size_t src_len) {
    char buf[10];
    if (src_len < sizeof(buf)) {
        strncpy(buf, src, src_len);
    }
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc > 1) {
        vulnerable_copy(argv[1]);
    }
    return 0;
}
