#include <stdint.h>
#include <stdio.h>

// Assembly function declaration
extern void vector_scale_asm(float* in, float* out, int len, float scale);

// Read cycle counter (RISC-V CSR)
static inline uint32_t rdcycle(void) {
    uint32_t cycles;
    asm volatile ("rdcycle %0" : "=r"(cycles));
    return cycles;
}

// Entry function with cycle measurement and firmware printf calls
// Returns: cycles elapsed (32-bit)
//
// FIRMWARE SYMBOL LINKING DEMONSTRATION:
// The printf() calls below are resolved by the JIT linker against the
// base firmware ELF file (firmware/build/p4_jit_firmware.elf).
// This demonstrates that JIT code can call ANY firmware function
// (malloc, free, FreeRTOS APIs, etc.) without reimplementing them.
//
// Output appears in device monitor (idf.py monitor), not Python.
uint32_t process_audio(float* input, float* output, int32_t len, float gain) {
    // Print processing info to device console
    printf("[JIT] process_audio() called\n");
    printf("[JIT] Array size: %d samples\n", len);
    printf("[JIT] Gain factor: %.2f\n", gain);
    printf("[JIT] Input buffer: %p\n", input);
    printf("[JIT] Output buffer: %p\n", output);
    
    uint32_t start = rdcycle();
    
    // Call optimized assembly kernel
    vector_scale_asm(input, output, len, gain);
    
    uint32_t end = rdcycle();
    uint32_t elapsed = end - start;
    
    // Print results to device console
    printf("[JIT] Processing complete: %u cycles\n", elapsed);
    printf("[JIT] Performance: %.2f cycles/sample\n", (float)elapsed / len);
    
    return elapsed;
}
