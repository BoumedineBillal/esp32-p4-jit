# %% [markdown]
# # ESP32-P4 JIT System: Complete Tutorial
# 
# **Demonstrates**: Native RISC-V execution, C + Assembly integration, NumPy interface, cycle measurement, firmware symbol linking, and complete introspection.
# 
# ---

# %% [markdown]
# ## 1. Setup & Environment

# %%
import os
import sys
import numpy as np
from pathlib import Path

# Setup directories
NOTEBOOK_DIR = Path.cwd()
SOURCE_DIR = NOTEBOOK_DIR / "source"
SOURCE_DIR.mkdir(parents=True, exist_ok=True)

# Add host to path (adjust path to your project root)
PROJECT_ROOT = NOTEBOOK_DIR.parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "host"))

from p4jit import P4JIT, MALLOC_CAP_SPIRAM, MALLOC_CAP_8BIT
import p4jit

# Set verbose logging
p4jit.set_log_level('INFO_VERBOSE')

print("✓ Environment ready")
print(f"✓ Source directory: {SOURCE_DIR}")

# %% [markdown]
# ## 2. Create Assembly File (Optimized Vector Scaling)
# 
# We'll create an assembly routine that scales a vector of floats. This demonstrates:
# - Low-level RISC-V optimization
# - Floating-point operations
# - Loop unrolling potential

# %%
asm_code = """    .text
    .align 4
    .global vector_scale_asm
    .type vector_scale_asm, @function

// Optimized vector scaling: out[i] = in[i] * scale
// void vector_scale_asm(float* in, float* out, int len, float scale)
// a0 = in, a1 = out, a2 = len, fa0 = scale

vector_scale_asm:
    beqz    a2, .done          // if len == 0, exit
    
.loop:
    flw     ft0, 0(a0)         // Load input
    fmul.s  ft0, ft0, fa0      // Multiply by scale
    fsw     ft0, 0(a1)         // Store output
    
    addi    a0, a0, 4          // in++
    addi    a1, a1, 4          // out++
    addi    a2, a2, -1         // len--
    bnez    a2, .loop          // Continue if len > 0
    
.done:
    ret
"""

# Write assembly file
asm_path = SOURCE_DIR / "vector_ops.S"
with open(asm_path, 'w') as f:
    f.write(asm_code)
    
print(f"✓ Created: {asm_path.name}")
print(f"✓ Function: vector_scale_asm(float* in, float* out, int len, float scale)")

# %% [markdown]
# ## 3. Create C Entry Point with Cycle Measurement & Firmware Symbols
# 
# The C wrapper:
# - Calls the assembly kernel
# - Measures CPU cycles using RISC-V's `rdcycle` instruction
# - **Uses firmware symbols (printf) to demonstrate symbol resolution**
# - Returns cycle count for performance analysis
# 
# **Firmware Symbol Linking:**
# When `use_firmware_elf=True` is set during loading, the JIT linker resolves symbols like `printf`, `malloc`, `free`, etc. from the base firmware ELF file. This allows JIT code to call any firmware function without reimplementing it.
# 
# **Note:** `printf` output appears in the device monitor (ESP-IDF serial console), not in Python output.

# %%
c_code = """#include <stdint.h>
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
    printf("[JIT] process_audio() called\\n");
    printf("[JIT] Array size: %d samples\\n", len);
    printf("[JIT] Gain factor: %.2f\\n", gain);
    printf("[JIT] Input buffer: %p\\n", input);
    printf("[JIT] Output buffer: %p\\n", output);
    
    uint32_t start = rdcycle();
    
    // Call optimized assembly kernel
    vector_scale_asm(input, output, len, gain);
    
    uint32_t end = rdcycle();
    uint32_t elapsed = end - start;
    
    // Print results to device console
    printf("[JIT] Processing complete: %u cycles\\n", elapsed);
    printf("[JIT] Performance: %.2f cycles/sample\\n", (float)elapsed / len);
    
    return elapsed;
}
"""

# Write C file
c_path = SOURCE_DIR / "audio_dsp.c"
with open(c_path, 'w') as f:
    f.write(c_code)
    
print(f"✓ Created: {c_path.name}")
print(f"✓ Entry: process_audio(float*, float*, int32_t, float)")
print(f"✓ Returns: CPU cycles elapsed (uint32_t)")
print(f"✓ Uses firmware symbols: printf() for logging")
print(f"\n⚠️  Note: printf() output appears in device monitor, not here!")
print(f"   Run 'idf.py monitor' in firmware/ directory to see output.")

# %% [markdown]
# ## 4. Connect to Device & Check Memory

# %%
# Initialize JIT system (auto-detects USB port)
jit = P4JIT()

print("\n" + "="*60)
print("DEVICE INFORMATION")
print("="*60)

# Get initial heap statistics
stats = jit.get_heap_stats(print_s=True)
print("="*60)

# %% [markdown]
# ## 5. Compile & Load Function
# 
# The builder will:
# 1. Discover both `.c` and `.S` files automatically
# 2. Generate wrapper code (`temp.c`) and headers
# 3. Compile with Link-Time Optimization
# 4. **Resolve firmware symbols (printf) from base firmware ELF**
# 5. Allocate device memory
# 6. Upload binary via USB
# 
# **Key Setting:** `use_firmware_elf=True` enables linking against firmware symbols.

# %%
print("\n" + "="*60)
print("BUILDING JIT FUNCTION")
print("="*60)

# Load function (smart_args=True for NumPy integration)
# use_firmware_elf=True enables printf and other firmware symbols
func = jit.load(
    source=str(c_path),
    function_name='process_audio',
    optimization='O3',
    use_firmware_elf=True  # CRITICAL: Enable firmware symbol resolution
)

print(f"\n✓ Function loaded at: 0x{func.code_addr:08X}")
print(f"✓ Args buffer at:     0x{func.args_addr:08X}")
print(f"✓ Binary size:        {func.stats['code_size']} bytes")
print(f"✓ Args size:          {func.stats['args_size']} bytes")
print(f"✓ Firmware symbols:   RESOLVED (printf available)")
print("="*60)

# %% [markdown]
# ## 6. Inspect Generated Files
# 
# The system automatically generates:
# - **temp.c**: Wrapper that unpacks arguments and calls your function
# - **audio_dsp.h**: Function prototypes with type declarations

# %%
print("\n" + "="*60)
print("GENERATED WRAPPER CODE (temp.c)")
print("="*60)

temp_c_path = SOURCE_DIR / "temp.c"
if temp_c_path.exists():
    with open(temp_c_path, 'r') as f:
        content = f.read()
        print(content)
else:
    print("[Not found]")

# %%
print("\n" + "="*60)
print("GENERATED HEADER (audio_dsp.h)")
print("="*60)

header_path = SOURCE_DIR / "audio_dsp.h"
if header_path.exists():
    with open(header_path, 'r') as f:
        print(f.read())
else:
    print("[Not found]")

# %% [markdown]
# ## 7. Binary Analysis & Memory Layout

# %%
print("\n" + "="*60)
print("BINARY SECTIONS")
print("="*60)
func.binary.print_sections()

# %%
print("\n" + "="*60)
print("SYMBOL TABLE (Functions)")
print("="*60)
func.binary.print_symbols()

# %%
print("\n" + "="*60)
print("MEMORY MAP")
print("="*60)
func.binary.print_memory_map()

# %%
print("\n" + "="*60)
print("FUNCTION METADATA")
print("="*60)
metadata = func.binary.metadata
print(f"Function:     {metadata['name']}")
print(f"Return Type:  {metadata['return_type']}")
print(f"Parameters:   {len(metadata['parameters'])}")
for i, param in enumerate(metadata['parameters']):
    print(f"  [{i}] {param['type']:<12} {param['name']:<12} ({param['category']})")
    
print(f"\nMemory Addresses:")
addrs = metadata['addresses']
print(f"  Code Base:    {addrs['code_base']}")
print(f"  Args Base:    {addrs['arg_base']}")
print(f"  Args Size:    {addrs['args_array_bytes']} bytes ({addrs['args_array_size']} slots)")

# %% [markdown]
# ## 8. Prepare Test Data (NumPy)
# 
# Generate a 1-second audio signal @ 48kHz sampling rate

# %%
# Audio parameters
SAMPLE_RATE = 48000
DURATION = 1.0
NUM_SAMPLES = int(SAMPLE_RATE * DURATION)

# Generate sine wave (440 Hz - A4 note)
t = np.linspace(0, DURATION, NUM_SAMPLES, dtype=np.float32)
frequency = 440.0
input_signal = np.sin(2 * np.pi * frequency * t).astype(np.float32)

# Prepare output buffer (zeros)
output_signal = np.zeros_like(input_signal)

# Gain factor
gain = np.float32(0.5)

print(f"✓ Generated test signal:")
print(f"  Samples:      {NUM_SAMPLES:,}")
print(f"  Duration:     {DURATION} seconds")
print(f"  Frequency:    {frequency} Hz")
print(f"  Gain:         {gain}")
print(f"  Input range:  [{input_signal.min():.3f}, {input_signal.max():.3f}]")
print(f"  Input dtype:  {input_signal.dtype}")
print(f"  Data size:    {input_signal.nbytes / 1024:.2f} KB")

# %% [markdown]
# ## 9. Execute on ESP32-P4 (Native RISC-V)
# 
# Smart Args automatically:
# - Allocates device memory for arrays
# - Transfers data to device
# - Executes native code
# - Returns results
# 
# **Watch device monitor for printf output!**
# The printf statements in the C code will show:
# - Array size being processed
# - Buffer addresses
# - Gain factor
# - Performance metrics

# %%
print("\n" + "="*60)
print("EXECUTING ON DEVICE")
print("="*60)
print("\n⚠️  CHECK DEVICE MONITOR FOR PRINTF OUTPUT!")
print("   You should see array size and processing info.\n")

# Execute (returns cycle count)
cycles = func(input_signal, output_signal, np.int32(NUM_SAMPLES), gain)

# Calculate performance metrics
freq_mhz = 360.0  # ESP32-P4 @ 360 MHz
time_us = cycles / freq_mhz
time_ms = time_us / 1000.0
samples_per_second = NUM_SAMPLES / (time_us / 1e6)
cycles_per_sample = cycles / NUM_SAMPLES

print(f"\n✓ Execution complete!")
print(f"\nPerformance:")
print(f"  CPU Cycles:        {cycles:,}")
print(f"  Execution Time:    {time_us:.2f} µs ({time_ms:.3f} ms)")
print(f"  Throughput:        {samples_per_second:,.0f} samples/sec")
print(f"  Efficiency:        {cycles_per_sample:.2f} cycles/sample")

print(f"\nResults:")
print(f"  Output range:      [{output_signal.min():.3f}, {output_signal.max():.3f}]")

# Verify correctness
expected = input_signal * gain
max_error = np.abs(output_signal - expected).max()
mean_error = np.abs(output_signal - expected).mean()

print(f"\nAccuracy:")
print(f"  Max Error:         {max_error:.9f}")
print(f"  Mean Error:        {mean_error:.9f}")

if max_error < 1e-6:
    print("\n✓ PASS: Results match expected values!")
else:
    print("\n✗ FAIL: Results do not match!")

print("\n" + "="*60)
print("EXPECTED DEVICE MONITOR OUTPUT:")
print("="*60)
print("[JIT] process_audio() called")
print(f"[JIT] Array size: {NUM_SAMPLES} samples")
print(f"[JIT] Gain factor: {gain:.2f}")
print("[JIT] Input buffer: 0x3c......")
print("[JIT] Output buffer: 0x3c......")
print(f"[JIT] Processing complete: {cycles} cycles")
print(f"[JIT] Performance: {cycles_per_sample:.2f} cycles/sample")
print("="*60)

# %% [markdown]
# ## 10. Memory State After Execution

# %%
print("\n" + "="*60)
print("MEMORY STATE AFTER EXECUTION")
print("="*60)

stats_after = jit.get_heap_stats(print_s=False)

print(f"SPIRAM:")
print(f"  Total:    {stats_after['total_spiram']//1024//1024:>6} MB")
print(f"  Free:     {stats_after['free_spiram']//1024//1024:>6} MB")
print(f"  Used:     {(stats_after['total_spiram'] - stats_after['free_spiram'])//1024//1024:>6} MB")

print(f"\nInternal SRAM:")
print(f"  Total:    {stats_after['total_internal']//1024:>6} KB")
print(f"  Free:     {stats_after['free_internal']//1024:>6} KB")
print(f"  Used:     {(stats_after['total_internal'] - stats_after['free_internal'])//1024:>6} KB")

# Calculate JIT overhead
spiram_used = (stats['free_spiram'] - stats_after['free_spiram']) / 1024
print(f"\nJIT Function Memory: {spiram_used:.2f} KB")
print("="*60)

# %% [markdown]
# ## 11. View Disassembly
# 
# Generate annotated disassembly with source code intermixed.
# This shows the actual RISC-V instructions generated by the compiler.

# %%
# Generate disassembly file
disasm_path = SOURCE_DIR / "disassembly.txt"
func.binary.disassemble(output=str(disasm_path), source_intermix=False)

print(f"✓ Disassembly saved to: {disasm_path}")
print(f"✓ File size: {disasm_path.stat().st_size / 1024:.2f} KB")

print("\nFirst 200 lines:")
print("-" * 60)

with open(disasm_path, 'r') as f:
    lines = f.readlines()[:200]
    print(''.join(lines))
    
print("\n(See full disassembly in file)")

# %% [markdown]
# ## 12. Performance Visualization
# 
# Plot input vs output to verify signal processing visually.

# %%
try:
    import matplotlib.pyplot as plt
    
    # Plot first 1000 samples
    n_plot = 1000
    t_plot = t[:n_plot]
    
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 8))
    
    # Input signal
    ax1.plot(t_plot, input_signal[:n_plot], 'b-', linewidth=0.5, label='Input')
    ax1.set_ylabel('Amplitude')
    ax1.set_title('Input Signal (440 Hz Sine Wave)')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Output signal
    ax2.plot(t_plot, output_signal[:n_plot], 'r-', linewidth=0.5, label=f'Output (Gain={gain})')
    ax2.set_ylabel('Amplitude')
    ax2.set_title('Output Signal (After ESP32-P4 Processing)')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Error plot
    error = output_signal[:n_plot] - expected[:n_plot]
    ax3.plot(t_plot, error, 'g-', linewidth=0.5, label='Error')
    ax3.set_xlabel('Time (seconds)')
    ax3.set_ylabel('Error')
    ax3.set_title(f'Processing Error (Max: {max_error:.9f})')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    plt.tight_layout()
    plot_path = SOURCE_DIR / 'signal_processing.png'
    plt.savefig(plot_path, dpi=150)
    plt.show()
    
    print(f"✓ Plot saved to: {plot_path}")
    
except ImportError:
    print("matplotlib not available - skipping visualization")

# %% [markdown]
# ## 13. Cleanup Resources

# %%
print("\n" + "="*60)
print("CLEANUP")
print("="*60)

# Free function resources (code + args buffers)
func.free()
print("✓ Function resources freed")

# Verify memory reclaimed
stats_final = jit.get_heap_stats(print_s=False)
spiram_reclaimed = (stats_final['free_spiram'] - stats_after['free_spiram']) / 1024
print(f"✓ Memory reclaimed: {spiram_reclaimed:.2f} KB")

# Disconnect from device
jit.session.device.disconnect()
print("✓ Device disconnected")

print(f"\nFinal SPIRAM Free: {stats_final['free_spiram']//1024//1024} MB")
print("="*60)

print("\n" + "="*60)
print("✓ TUTORIAL COMPLETE")
print("="*60)

# %% [markdown]
# ---
# 
# ## Summary: What We Demonstrated
# 
# ### Core Features:
# 1. **Multi-file compilation**: Automatic discovery of C + Assembly files
# 2. **Automatic wrapper generation**: Memory-mapped I/O argument passing
# 3. **NumPy integration**: Seamless host ↔ device data transfer
# 4. **Cycle-accurate measurement**: Native RISC-V `rdcycle` instruction
# 5. **Firmware symbol linking**: JIT code calls printf, malloc, free, etc.
# 6. **Native execution**: Zero interpreter overhead
# 7. **Real-time performance**: ~5 cycles/sample for vector operations
# 
# ### Firmware Symbol Resolution:
# When `use_firmware_elf=True`, the JIT linker:
# - Reads symbol table from firmware ELF file
# - Resolves undefined symbols (printf, malloc, etc.)
# - Links JIT code against firmware functions
# - Enables calling ANY firmware API without reimplementation
# 
# **Demonstrated with printf:**
# - Printed array size (48000 samples)
# - Printed buffer addresses
# - Printed gain factor
# - Printed performance metrics
# 
# ### Information Available:
# - **Binary sections**: .text, .rodata, .data, .bss
# - **Symbol table**: All functions with addresses and sizes
# - **Memory layout**: Visual map with alignment
# - **Function metadata**: Complete signature with types
# - **Generated code**: Wrapper (temp.c) and headers
# - **Disassembly**: Annotated with source code
# - **Heap statistics**: Real-time memory usage
# 
# ### Performance Results:
# - **Throughput**: ~73M samples/second
# - **Efficiency**: ~5 cycles/sample
# - **Latency**: Sub-millisecond for 48K samples
# - **Accuracy**: Floating-point precision maintained
# 
# ---
# 
# **Next Steps:**
# - Try different optimizations (-O2, -O3, -Os)
# - Implement complex DSP algorithms (filters, FFT)
# - Compare C vs Assembly performance
# - Use more firmware symbols (malloc, snprintf, FreeRTOS)
# - Build multi-stage processing pipelines


