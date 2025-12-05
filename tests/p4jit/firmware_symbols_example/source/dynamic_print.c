#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/**
 * Test function to demonstrate usage of firmware symbols.
 * 
 * This function relies on the JIT linker resolving symbols like:
 * - printf
 * - malloc
 * - free
 * - snprintf
 * against the base firmware ELF.
 */
int test_dynamic(void) {
    printf("[JIT] Starting dynamic allocation test...\n");
    
    // 1. Test Malloc
    printf("[JIT] Allocating 64 bytes...\n");
    char *buffer = (char *)malloc(64);
    
    if (buffer == NULL) {
        printf("[JIT] Error: malloc failed!\n");
        return -1;
    }
    
    printf("[JIT] Memory allocated at: %p\n", buffer);
    
    // 2. Test String Operations (snprintf)
    snprintf(buffer, 64, "Hello from JIT Heap! (Magic: 0x%X)", 0xDEADBEEF);
    
    // 3. Test Printf with string from heap
    printf("[JIT] Buffer content: %s\n", buffer);
    
    // 4. Test Free
    free(buffer);
    printf("[JIT] Memory freed.\n");
    
    return 42; // Return success code
}
