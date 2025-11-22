# Rompler DSP Test Case

This test case evaluates the performance and correctness of a "Rompler" voice engine implementation on the ESP32-P4 using the JIT framework. It simulates a sample playback engine with pitch shifting and dynamic anti-aliasing filters.

## Overview

The test processes a large audio buffer in blocks, simulating a real-time audio rendering workload. For each block:
1.  **Pitch Shifting**: Calculates the required input samples based on the playback pitch (phase increment).
2.  **Anti-Aliasing**: If the pitch is shifted down (or up significantly), it calculates and applies a low-pass filter (LPF) to prevent aliasing artifacts.
3.  **Biquad Filtering**: The LPF is implemented as a cascade of 3 biquad filters.

## Implementations Tested

The test compares three different implementations of the core processing logic:

1.  **C Implementation (`Rompler_ApplyToLargeBuffer`)**:
    *   Pure C implementation of the biquad filter and block processing.
    *   Serves as the baseline for correctness and performance.

2.  **ASM Fused Implementation (`Rompler_ApplyToLargeBuffer2`)**:
    *   Uses a hand-optimized assembly function `dsps_biquad_f32_cascade3_arp4`.
    *   **Fused Loop**: Processes all 3 biquad stages within a single loop over the sample buffer.
    *   **ILP Optimization**: Instructions are reordered to maximize Instruction Level Parallelism, allowing independent floating-point operations (feedback vs. feedforward paths) to execute concurrently.
    *   **Stack Reduction**: Optimized stack frame usage (24 bytes) for faster function calls.

3.  **ASM Single Implementation (`Rompler_ApplyToLargeBuffer3`)**:
    *   Uses a hand-optimized assembly function `dsps_biquad_f32_arp4`.
    *   Standard single biquad implementation, called 3 times sequentially for the cascade.
    *   Useful for benchmarking the overhead of function calls and loop setup vs. the fused approach.

## Usage

Run the test script from the project root:

```bash
python tests/test_rompler/test_rompler.py
```

## Output

The script generates:

1.  **Performance Table**: A detailed table comparing execution time (us), CPU cycles, and binary size for all implementations across multiple test cases.
    *   *No Pitch Shift*: Baseline copy (no filtering).
    *   *Pitch Up (LPF)*: Heavy filtering workload.
    *   *Pitch Down*: Interpolation workload.
    *   *Extreme Pitch*: Stress test.
    *   Includes percentage improvement of ASM versions over C.
    *   Saved as `rompler_performance_table.png`.

2.  **Validation Plots**:
    *   **Signal Overlay**: Compares JIT output (Red) vs. Python Reference (Black).
    *   **Error Plot**: Shows the absolute difference (error) between JIT and Reference.
    *   **Spectrogram**: Visualizes the frequency content of the output.
    *   Saved as `rompler_C_Implementation.png`, `rompler_ASM_Implementation.png`, etc.

3.  **Console Output**: Real-time progress, cycle counts, and a text-based summary table.

## Key Optimizations

The `dsps_biquad_cascade3_arp4.S` assembly file features:
*   **Parallel Execution**: Feedback (poles) and Feedforward (zeros) paths are interleaved to hide FPU latencies.
*   **Register Reuse**: State variables (`w0`, `w1`) are kept in registers (`fs0`-`fs5`) across the loop to minimize memory access.
*   **Reduced Overhead**: Fusing 3 stages into one function eliminates the overhead of 2 function calls and 2 loop setups per block.

## Memory Layout

*   **Code**: Allocated in `MALLOC_CAP_INTERNAL` (SRAM) for fast instruction fetch.
*   **Data**: Allocated in `MALLOC_CAP_INTERNAL` (SRAM) for fast data access.
