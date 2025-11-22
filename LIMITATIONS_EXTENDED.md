# ESP32-P4 JIT System - Advanced Configuration & Limitations (Part 2)

This document serves as a continuation of `LIMITATIONS.md`, focusing on advanced memory configurations, hardware protection mechanisms, and performance tuning for the ESP32-P4.

---

## Table of Contents

- [Internal Memory Execution (L2MEM)](#internal-memory-execution-l2mem)
- [Hardware Memory Protection (PMP/PMA)](#hardware-memory-protection-pmppma)
- [Performance Tuning](#performance-tuning)
- [Safety Implications](#safety-implications)

---

## Internal Memory Execution (L2MEM)

### The Challenge
By default, the ESP32-P4 prevents code execution from Internal Data Memory (L2MEM, address range `0x4FF00000` - `0x4FFBFFFF`). Attempting to jump to code located in this region results in a `Guru Meditation Error: Instruction access fault`.

### The Solution
To enable execution from L2MEM, you must disable the strict separation between Instruction RAM (IRAM) and Data RAM (DRAM) in the firmware configuration.

**Required `sdkconfig` Change:**
```makefile
# Disable strict PMP/PMA split to allow execution from data memory
CONFIG_ESP_SYSTEM_PMP_IDRAM_SPLIT=n
```

### How It Works
*   **Default (`y`)**: The startup code configures the RISC-V Physical Memory Protection (PMP) and Physical Memory Attributes (PMA) units to mark DRAM regions as **Non-Executable (NX)**. This is a security feature to prevent code injection attacks.
*   **Disabled (`n`)**: The startup code relaxes these protections, mapping the memory as **Read-Write-Execute (RWX)**. This allows the JIT system to allocate memory in L2MEM (using `MALLOC_CAP_INTERNAL`) and execute it.

---

## Hardware Memory Protection (PMP/PMA)

The ESP32-P4 utilizes standard RISC-V hardware units for memory protection:

1.  **PMP (Physical Memory Protection)**: Enforces permissions (R/W/X) on physical address ranges for different privilege modes (Machine/User).
2.  **PMA (Physical Memory Attributes)**: Defines attributes (Cacheable, Idempotent, Atomic) and permissions for physical memory regions.

### Configuration Impact
When `CONFIG_ESP_SYSTEM_PMP_IDRAM_SPLIT` is enabled (default), the firmware effectively creates a "W^X" (Write XOR Execute) policy for internal memory:
*   **IRAM**: Executable, Read-Only (via Instruction Bus).
*   **DRAM**: Read-Write, Non-Executable (via Data Bus).

Disabling this feature is **mandatory** for JIT systems that wish to use internal SRAM for code storage, as the ESP32-P4 does not have a dedicated "JIT" memory region that is natively RWX without configuration changes.

---

## Performance Tuning

### L2MEM vs. PSRAM
The ESP32-P4 memory hierarchy presents a trade-off between latency and capacity.

| Feature | L2MEM (Internal SRAM) | PSRAM (External RAM) |
| :--- | :--- | :--- |
| **Capacity** | ~768 KB (Available) | 16 MB - 32 MB |
| **Access Type** | Direct / L2 Cache | Via L2 Cache |
| **Latency** | Low (SRAM speed) | Higher (SPI transaction) |
| **JIT Suitability** | Small, hot code loops | Large applications |
| **Configuration** | Requires `PMP_IDRAM_SPLIT=n` | Works by default (XIP) |

### Optimization Strategy
1.  **Use PSRAM by Default**: For most applications, the performance difference is negligible due to the efficient L1/L2 caches. Code in PSRAM is cached into the L1 Instruction Cache, executing at near-native speed after the first "warm-up" iteration.
2.  **Use L2MEM for Critical Loops**: If you have small, extremely latency-sensitive code (e.g., tight DSP loops, interrupt handlers) that suffers from cache miss penalties, place it in L2MEM.
3.  **Warm-Up is Critical**: Regardless of memory type, always run a "warm-up" iteration of your JIT code to ensure instructions are loaded into the L1 Cache before measuring performance.

---

## Safety Implications

Disabling `CONFIG_ESP_SYSTEM_PMP_IDRAM_SPLIT` reduces the system's defense-in-depth against security vulnerabilities.

### Risks
*   **Code Injection**: If an attacker can write to memory (e.g., via a buffer overflow), they can now execute that payload directly.
*   **Accidental Execution**: A wild function pointer could jump into data memory and interpret random data as instructions, leading to unpredictable behavior instead of an immediate crash.

### Mitigation
*   **Development Only**: It is recommended to enable L2MEM execution primarily for development, debugging, and specific high-performance use cases.
*   **Input Validation**: Ensure strict validation of all data entering the system to prevent buffer overflows.
*   **Sandboxing**: The current JIT system runs in Machine Mode (M-Mode) with full privileges. There is no sandboxing between the JIT code and the firmware.

---

---

## Parser & Signature Constraints

The JIT system uses a regex-based parser to extract function signatures. This imposes specific formatting requirements on your C source code.

### Function Definition Formatting
The entry function definition **must be written on its own line**. Do not combine it with other statements or variable declarations on the same line.

**Incorrect:**
```c
int p=7; int add(int a) { return a + p; }
```

**Correct:**
```c
int p=7;
int add(int a) { 
    return a + p; 
}
```

### Custom Typedefs
If you use any `typedef` in your function signature (arguments or return type), that typedef **must also be defined** in `config/std_types.h`. The parser pre-pends `std_types.h` to your source code snippet during analysis. If the typedef is missing there, the parser will fail to recognize the type.

**Example:**
If you have:
```c
typedef struct { float x, y; } Point;
void process_point(Point p) { ... }
```

You must add `typedef struct { float x, y; } Point;` to `config/std_types.h` (or use standard types in the signature).

---

**Related Documents:**
*   [LIMITATIONS.md](./LIMITATIONS.md) - Core system limitations (Types, ABI, Threading).
*   [README.md](./README.md) - General system overview and usage.
