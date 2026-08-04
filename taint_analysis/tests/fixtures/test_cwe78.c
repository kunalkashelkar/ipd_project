// test_cwe78.c
// A minimal vulnerable C file that accepts input from the environment 
// and passes it to system() (Command Injection), along with a sanitized safe variant.

#include <stdlib.h>
#include <string.h>

void vulnerable_function() {
    // CWE-78 OS Command Injection
    // Source: getenv()
    // Sink: system()
    
    char* data;
    data = getenv("ADD"); // Source
    
    if (data != NULL) {
        char dest[100] = "";
        strcat(dest, data);
        system(dest); // Sink
    }
}

void safe_function() {
    // Variant with a basic sanitizer (whitelist check)
    // Source: getenv()
    // Sanitizer: strncmp
    // Sink: system()
    
    char* data;
    data = getenv("ADD"); // Source
    
    if (data != NULL) {
        // Safe check
        if (strncmp(data, "safe_cmd", 8) == 0) {
            char dest[100] = "";
            strcat(dest, data);
            system(dest); // Sink
        }
    }
}

int main(int argc, char *argv[]) {
    vulnerable_function();
    safe_function();
    return 0;
}
