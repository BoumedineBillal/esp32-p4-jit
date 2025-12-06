# ESP32-P4 JIT: Dynamic Code Loading for ESP32-P4

**Compile C/C++ on your PC, execute natively on ESP32-P4 — No firmware reflashing required.**

![System Architecture](assets/system-architecture.jpeg)

P4-JIT is a sophisticated dynamic code loading system that enables you to write, compile, and execute native RISC-V machine code on the ESP32-P4 microcontroller in seconds, not minutes. Perfect for rapid algorithm development, DSP prototyping, and machine learning kernel optimization.

---

## 🎯 The Power of Python + Native Performance

**P4-JIT bridges two worlds: Python's rich ecosystem and embedded native performance.**

### The Complete Workflow:

```
┌─────────────────────────────────────────────────────────────────┐
│  Python Ecosystem (Host PC)                                     │
│  ├─ Generate test data (NumPy, Pandas, SciPy)                   │
│  ├─ Prepare inputs (image processing, signal generation)        │
│  └─ Load data into NumPy arrays                                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Automatic transfer (USB High-Speed)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  ESP32-P4 (Native RISC-V)                                       │
│  ├─ Execute compute-intensive kernels at 360 MHz                │
│  ├─ Process data with zero interpreter overhead                 │
│  └─ Modify arrays in-place (optional sync-back)                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Automatic return (results in NumPy arrays)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  Python Ecosystem (Host PC)                                     │
│  ├─ Visualize results (Matplotlib, Plotly, Seaborn)             │
│  ├─ Analyze performance (timeit, profiling)                     │
│  ├─ Compare algorithms (A/B testing)                            │
│  └─ Export data (CSV, HDF5, JSON)                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Features

- **Native Performance**: Direct RISC-V execution, zero interpreter overhead
- **Rapid Iteration**: 1-2 second cycles vs 30-60 seconds for full firmware rebuild
- **Smart Arguments**: Automatic NumPy ↔ C type conversion and memory management
- **Multi-File Projects**: Automatic source file discovery and Link-Time Optimization
- **Symbol Bridge**: Call firmware functions (`printf`, `malloc`, FreeRTOS APIs) directly
- **Type Safe**: Runtime validation prevents type mismatches
- **Memory Safe**: Host-side bounds checking prevents device crashes

---


![c function lifecycle diagram](assets/c-function-lifecycle-diagram.jpeg)



## ⚠️ CRITICAL: Initial Setup (Do This First!)

### Step 1: Install ESP-IDF v5.x (Required)

**P4-JIT requires the ESP-IDF toolchain to be installed on your system.**

1. **Download and install ESP-IDF v5.x or later**:
   - Follow the official guide: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/

2. **Verify installation**:
   ```bash
   # Linux/macOS
   . $HOME/esp/esp-idf/export.sh
   
   # Windows
   %userprofile%\esp\esp-idf\export.bat
   ```

3. **Check toolchain is available**:
   ```bash
   riscv32-esp-elf-gcc --version
   # Should show: riscv32-esp-elf-gcc (crosstool-NG esp-...) 13.2.0 or later
   ```

---

### Step 2: Configure Toolchain Path (CRITICAL!)

**⚠️ THE PROJECT WILL NOT WORK WITHOUT THIS STEP ⚠️**

The entire P4-JIT system relies on the RISC-V toolchain path being correctly configured. This tells the build system where to find the compiler, linker, and other tools.

#### Find Your Toolchain Path

**Linux/macOS**:
```bash
which riscv32-esp-elf-gcc
# Example output: /home/user/.espressif/tools/riscv32-esp-elf/esp-13.2.0_20230928/riscv32-esp-elf/bin/riscv32-esp-elf-gcc
# Your path is: /home/user/.espressif/tools/riscv32-esp-elf/esp-13.2.0_20230928/riscv32-esp-elf/bin
```

**Windows**:
```cmd
where riscv32-esp-elf-gcc
# Example output: C:\Users\YourName\.espressif\tools\riscv32-esp-elf\esp-13.2.0_20230928\riscv32-esp-elf\bin\riscv32-esp-elf-gcc.exe
# Your path is: C:\Users\YourName\.espressif\tools\riscv32-esp-elf\esp-13.2.0_20230928\riscv32-esp-elf\bin
```

**Common Locations**:
- **Linux**: `~/.espressif/tools/riscv32-esp-elf/esp-XX.X.X_XXXXXXXX/riscv32-esp-elf/bin`
- **macOS**: `~/.espressif/tools/riscv32-esp-elf/esp-XX.X.X_XXXXXXXX/riscv32-esp-elf/bin`
- **Windows**: `C:\Users\<Username>\.espressif\tools\riscv32-esp-elf\esp-XX.X.X_XXXXXXXX\riscv32-esp-elf\bin`
- **Windows (Espressif IDE)**: `C:\Espressif\tools\riscv32-esp-elf\esp-XX.X.X_XXXXXXXX\riscv32-esp-elf\bin`

#### Update Configuration File

**Edit `config/toolchain.yaml`**:

```yaml
toolchain:
  path: "YOUR_TOOLCHAIN_PATH_HERE"  # ← PUT YOUR PATH HERE
  prefix: "riscv32-esp-elf"
  compilers:
    gcc: "riscv32-esp-elf-gcc"
    g++: "riscv32-esp-elf-g++"
    as: "riscv32-esp-elf-as"

# Rest of the file can stay as-is
```

**Example (Linux)**:
```yaml
toolchain:
  path: "/home/billal/.espressif/tools/riscv32-esp-elf/esp-13.2.0_20230928/riscv32-esp-elf/bin"
```

**Example (Windows)**:
```yaml
toolchain:
  path: "C:/Users/Billal/.espressif/tools/riscv32-esp-elf/esp-13.2.0_20230928/riscv32-esp-elf/bin"
```

**⚠️ Use forward slashes (`/`) even on Windows in the YAML file!**

---

### Step 3: Install Python Dependencies

```bash
cd host
pip install -r requirements.txt
```

**Required packages**:
- `pyserial` - USB communication
- `numpy` - Array handling
- `pycparser` - C code parsing
- `pyyaml` - Configuration

---

### Step 4: Build and Flash Firmware

```bash
cd firmware
idf.py set-target esp32p4
idf.py build
idf.py flash monitor
```

**Expected output**:
```
I (XXX) main: Starting P4-JIT Firmware
I (XXX) p4_jit: JIT Engine started in background task.
I (XXX) main: JIT Engine ready. Connect via USB.
```

Keep the monitor running or close it with `Ctrl+]`.

---

### Step 5: Verify Connection

Create a test script `test_connection.py`:

```python
from p4jit import P4JIT

try:
    jit = P4JIT()  # Auto-detects USB port
    print("✓ Connected to ESP32-P4!")
    
    stats = jit.get_heap_stats()
    print(f"✓ Device has {stats['total_spiram']//1024//1024} MB PSRAM")
    
except Exception as e:
    print(f"✗ Connection failed: {e}")
    print("\nTroubleshooting:")
    print("1. Is the device connected via USB?")
    print("2. Is the firmware running? (check monitor)")
    print("3. Is another program using the serial port?")
```

Run it:
```bash
python test_connection.py
```

**Success output**:
```
✓ Connected to ESP32-P4!
✓ Device has 32 MB PSRAM
```

---

## 📖 Quick Start: Your First JIT Function

### Example: Simple Addition

Create `examples/hello_add.py`:

```python
import numpy as np
from p4jit import P4JIT

# Write C source code directly in Python
c_source = """
int add(int a, int b) {
    return a + b;
}
"""

# Save to file
with open('add.c', 'w') as f:
    f.write(c_source)

# Initialize JIT system
jit = P4JIT()

# Compile, upload, and load function
print("Loading function...")
func = jit.load(source='add.c', function_name='add')

# Call it with NumPy types
result = func(np.int32(10), np.int32(20))

print(f"10 + 20 = {result}")  # Output: 10 + 20 = 30

# Cleanup
func.free()
```

Run it:
```bash
python examples/hello_add.py
```

**Expected output**:
```
Loading function...
Pass 1: Preliminary Build
Allocating device memory
Pass 2: Re-linking with allocated addresses
Uploading binary to device
Function loaded successfully.
10 + 20 = 30
```

**That's it! You just compiled C code on your PC and executed it natively on the ESP32-P4!**

---

## 🎯 How to Create New JIT Code

### Method 1: Inline C Code (Quick Prototyping)

```python
import numpy as np
from p4jit import P4JIT

# Define C function
c_code = """
float compute(float x, float y) {
    return x * x + y * y;
}
"""

# Write, compile, execute
with open('compute.c', 'w') as f:
    f.write(c_code)

jit = P4JIT()
func = jit.load(source='compute.c', function_name='compute')

result = func(np.float32(3.0), np.float32(4.0))
print(f"Result: {result}")  # 25.0
```

---

### Method 2: Separate Source Files (Organized Projects)

**File structure**:
```
my_project/
├── source/
│   ├── algorithm.c
│   └── helpers.c  # Automatically discovered!
└── test_algorithm.py
```

**source/algorithm.c**:
```c
#include <stdint.h>

// Helper function (can be in separate file)
extern int32_t square(int32_t x);

int32_t compute(int32_t a, int32_t b) {
    return square(a) + square(b);
}
```

**source/helpers.c**:
```c
#include <stdint.h>

int32_t square(int32_t x) {
    return x * x;
}
```

**test_algorithm.py**:
```python
import numpy as np
from p4jit import P4JIT

jit = P4JIT()

# Builder automatically finds and compiles ALL .c files in source/
func = jit.load(
    source='source/algorithm.c',  # Entry file
    function_name='compute'
)

result = func(np.int32(3), np.int32(4))
print(f"3² + 4² = {result}")  # 25
```

**Multi-file compilation is automatic!** The builder discovers all `.c`, `.cpp`, `.S` files in the same directory.

---

### Method 3: Using Firmware Functions (Symbol Bridge)

Call `printf`, `malloc`, and other firmware functions directly:

```python
from p4jit import P4JIT

c_code = """
#include <stdio.h>
#include <stdlib.h>

int test_firmware_calls(void) {
    printf("Hello from JIT!\\n");
    
    // Allocate memory using firmware's malloc
    int *data = (int*)malloc(10 * sizeof(int));
    if (data) {
        data[0] = 42;
        printf("Allocated and set data[0] = %d\\n", data[0]);
        free(data);
    }
    
    return 0;
}
"""

with open('firmware_test.c', 'w') as f:
    f.write(c_code)

jit = P4JIT()

# Enable symbol bridge
func = jit.load(
    source='firmware_test.c',
    function_name='test_firmware_calls',
    use_firmware_elf=True  # ← Enable firmware symbol resolution
)

func()

# Output (on device monitor):
# Hello from JIT!
# Allocated and set data[0] = 42
```

**Check device monitor (`idf.py monitor`) to see printf output!**

---

## 📚 Examples & Test Suite

All examples are located in `tests/p4jit/`. Each example is self-contained and demonstrates a specific feature.

### Example 1: Basic Math Operations

**File**: `tests/p4jit/workflow_example/test_workflow.py`

```python
"""
Example: Array Processing with Full Workflow
Demonstrates: Array pointers, Smart Args, Binary inspection
"""

import numpy as np
from p4jit import P4JIT

# C source code
c_source = """
#include <stdint.h>

// Apply gain to audio samples
float apply_gain(uint8_t* data, int len, float gain) {
    for(int i=0; i<len; i++) {
        float val = (float)data[i] * gain;
        if (val > 255.0f) val = 255.0f;
        data[i] = (uint8_t)val;
    }
    return gain;
}
"""

# Write source
with open('audio_processing.c', 'w') as f:
    f.write(c_source)

# Initialize
jit = P4JIT()

# Load function
func = jit.load(
    source='audio_processing.c',
    function_name='apply_gain'
)

# Create test data
input_data = np.random.randint(0, 100, 1024, dtype=np.uint8)
gain = np.float32(1.5)

print(f"Input (first 5): {input_data[:5]}")

# Execute
result = func(input_data, np.int32(len(input_data)), gain)

print(f"Output (first 5): {input_data[:5]}")
print(f"Gain applied: {result}")

# Inspect the compiled binary
print(f"\nBinary size: {func.binary.total_size} bytes")
func.binary.print_sections()
func.binary.print_memory_map()

# Save disassembly
func.binary.disassemble(output='disassembly.txt')
print("Disassembly saved to disassembly.txt")

# Cleanup
func.free()
```

**Run it**:
```bash
cd tests/p4jit/workflow_example
python test_workflow.py
```

---

### Example 2: Advanced Types (Structs)

**File**: `tests/p4jit/advanced_example/test_advanced.py`

> **⚠️ IMPORTANT: Custom Typedefs in Function Signatures**
>
> If you use a **custom typedef** (like `Point`) in your **entry function signature** (parameters or return type), you **MUST** add the typedef definition to `config/std_types.h`.
>
> **Why?** The signature parser prepends `std_types.h` before parsing your function signature. If your custom type isn't defined there, the parser will fail.
>
> **Example - Add to `config/std_types.h`**:
> ```c
> typedef struct {
>     float x;
>     int y;
> } Point;
> ```
>
> **Note**: This is only required if the type appears in the **function signature**. Types used only inside the function body don't need to be in `std_types.h`.


```python
"""
Example: Working with Structs and Pointers
Demonstrates: Custom types, manual memory management, multiple pointer arguments
"""

import struct
import numpy as np
from p4jit import P4JIT, MALLOC_CAP_SPIRAM, MALLOC_CAP_8BIT

# C source code
c_source = """
#include <stdint.h>

typedef struct {
    float x;
    int y;
} Point;

float sum_point(Point* p, int8_t z, uint16_t* arr) {
    return p->x + (float)p->y + (float)z + (float)arr[0];
}
"""

with open('geometry.c', 'w') as f:
    f.write(c_source)

jit = P4JIT()

# Load function with Smart Args disabled for manual control
func = jit.load(
    source='geometry.c',
    function_name='sum_point',
    smart_args=False  # Manual memory management
)

device = jit.session.device

# Prepare struct data: Point { float x; int y; }
struct_data = struct.pack("<fi", 10.5, 20)  # x=10.5, y=20
struct_addr = device.allocate(len(struct_data), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT, 16)
device.write_memory(struct_addr, struct_data)
print(f"Struct at 0x{struct_addr:08X}")

# Prepare array data: uint16_t arr[] = {100}
arr_data = struct.pack("<H", 100)
arr_addr = device.allocate(len(arr_data), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT, 16)
device.write_memory(arr_addr, arr_data)
print(f"Array at 0x{arr_addr:08X}")

# Prepare scalar: int8_t z = -5
z_val = -5

# Pack arguments manually (pointer, int8_t, pointer)
args_blob = struct.pack("<IiI", struct_addr, z_val, arr_addr)

# Execute
func(args_blob)

# Read result from slot 31 (offset 124)
result_addr = func.args_addr + 124
result_bytes = device.read_memory(result_addr, 4)
result = struct.unpack("<f", result_bytes)[0]

print(f"Result: {result}")  # 10.5 + 20 + (-5) + 100 = 125.5

# Cleanup
device.free(struct_addr)
device.free(arr_addr)
func.free()
```

**Run it**:
```bash
cd tests/p4jit/advanced_example
python test_advanced.py
```

---

### Example 3: Bidirectional Array Sync

**File**: `tests/p4jit/bidirectional_sync_example/test_bidirectional.py`

```python
"""
Example: Automatic Array Synchronization
Demonstrates: Arrays modified on device are updated on host automatically
"""

import numpy as np
from p4jit import P4JIT

# C source code
c_source = """
#include <stdint.h>

// Modify array in-place
int modify_array(int* data, int len) {
    for(int i = 0; i < len; i++) {
        data[i] = data[i] * 2;
    }
    return data[0];
}
"""

with open('bidirectional.c', 'w') as f:
    f.write(c_source)

jit = P4JIT()
func = jit.load(source='bidirectional.c', function_name='modify_array')

# Test 1: Sync ENABLED (default)
print("Test 1: Sync enabled")
data = np.array([1, 2, 3, 4], dtype=np.int32)
print(f"  Before: {data}")

ret_val = func(data, np.int32(len(data)))

print(f"  After:  {data}")  # [2, 4, 6, 8] - MODIFIED!
print(f"  Return: {ret_val}")  # 2

# Test 2: Sync DISABLED
print("\nTest 2: Sync disabled")
func.sync_arrays = False  # Disable sync

data2 = np.array([10, 20, 30, 40], dtype=np.int32)
print(f"  Before: {data2}")

func(data2, np.int32(len(data2)))

print(f"  After:  {data2}")  # [10, 20, 30, 40] - NOT modified
print("  (Data not synced back)")

func.free()
```

**Run it**:
```bash
cd tests/p4jit/bidirectional_sync_example
python test_bidirectional.py
```

---

### Example 4: Using Firmware Symbols

**File**: `tests/p4jit/firmware_symbols_example/test_firmware_symbols.py`

```python
"""
Example: Calling Firmware Functions
Demonstrates: printf, malloc, free from JIT code
"""

from p4jit import P4JIT

# C source code
c_source = """
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int test_dynamic(void) {
    printf("[JIT] Starting dynamic allocation test...\\n");
    
    // Test malloc
    printf("[JIT] Allocating 64 bytes...\\n");
    char *buffer = (char *)malloc(64);
    
    if (buffer == NULL) {
        printf("[JIT] Error: malloc failed!\\n");
        return -1;
    }
    
    printf("[JIT] Memory allocated at: %p\\n", buffer);
    
    // Test snprintf
    snprintf(buffer, 64, "Hello from JIT Heap! (Magic: 0x%X)", 0xDEADBEEF);
    
    // Test printf with heap string
    printf("[JIT] Buffer content: %s\\n", buffer);
    
    // Test free
    free(buffer);
    printf("[JIT] Memory freed.\\n");
    
    return 42;
}
"""

with open('dynamic_print.c', 'w') as f:
    f.write(c_source)

jit = P4JIT()

# Load with symbol bridge enabled
func = jit.load(
    source='dynamic_print.c',
    function_name='test_dynamic',
    use_firmware_elf=True  # ← Enable firmware symbol resolution
)

print("Executing function (check device monitor for output)...")
result = func()

print(f"Function returned: {result}")

# Expected output on device monitor:
# [JIT] Starting dynamic allocation test...
# [JIT] Allocating 64 bytes...
# [JIT] Memory allocated at: 0x3c0xxxxx
# [JIT] Buffer content: Hello from JIT Heap! (Magic: 0xDEADBEEF)
# [JIT] Memory freed.

func.free()
```

**Run it** (keep device monitor open):
```bash
cd tests/p4jit/firmware_symbols_example
python test_firmware_symbols.py
```

---

### Example 5: Heap Monitoring

**File**: `tests/p4jit/heap_info_example/test_heap_info.py`

```python
"""
Example: Real-time Heap Monitoring
Demonstrates: Querying device memory statistics
"""

from p4jit import P4JIT, MALLOC_CAP_SPIRAM, MALLOC_CAP_8BIT

jit = P4JIT()

# Get initial heap statistics
print("Initial heap state:")
stats_initial = jit.get_heap_stats(print_s=True)

# Allocate 1MB
print("\n[Allocating 1MB SPIRAM...]")
size = 1024 * 1024
addr = jit.session.device.allocate(size, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT, 16)
print(f"  Allocated at 0x{addr:08X}")

# Check heap after allocation
print("\nHeap after allocation:")
stats_post = jit.get_heap_stats(print_s=True)

# Verify allocation
diff = stats_initial['free_spiram'] - stats_post['free_spiram']
print(f"\nFree SPIRAM decreased by: {diff} bytes ({diff/1024:.2f} KB)")

# Free memory
jit.session.device.free(addr)
print("\n[Freed Memory]")

# Check heap after free
print("\nHeap after free:")
stats_final = jit.get_heap_stats(print_s=True)

if stats_final['free_spiram'] > stats_post['free_spiram']:
    print("\n✓ Memory successfully reclaimed")
```

**Run it**:
```bash
cd tests/p4jit/heap_info_example
python test_heap_info.py
```

---

### Example 6: Logging Control

**File**: `tests/p4jit/simple_logging_example/test_simple_logging.py`

```python
"""
Example: Controlling Log Verbosity
Demonstrates: INFO, INFO_VERBOSE, DEBUG levels
"""

import p4jit

print("=== Logging Levels Demo ===\n")

# Level 1: INFO (default) - High-level milestones only
print("1. INFO Level (default)")
p4jit.set_log_level('INFO')
jit = p4jit.P4JIT()
print()

# Level 2: INFO_VERBOSE - Detailed operational steps
print("2. INFO_VERBOSE Level")
p4jit.set_log_level('INFO_VERBOSE')
# Now you'll see: "Compiling...", "Linking...", "Allocating..."
print()

# Level 3: DEBUG - Everything including internal data
print("3. DEBUG Level")
p4jit.set_log_level('DEBUG')
# Now you'll see: Command hex dumps, register values, checksums, etc.
print()

print("Use p4jit.set_log_level('LEVEL') to control verbosity")
print("Available levels: DEBUG, INFO_VERBOSE, INFO, WARNING, ERROR, CRITICAL")
```

**Run it**:
```bash
cd tests/p4jit/simple_logging_example
python test_simple_logging.py
```

---

## 🗂️ Project Structure

```
p4-jit/
├── host/                          # Host-side Python toolchain
│   └── p4jit/
│       ├── __init__.py
│       ├── p4jit.py               # Main API: P4JIT, JITFunction
│       ├── runtime/               # Device communication & execution
│       │   ├── device_manager.py  # Protocol implementation, shadow allocation table
│       │   ├── jit_session.py     # Connection management, device discovery
│       │   ├── remote_function.py # Function call wrapper
│       │   ├── smart_args.py      # Automatic type conversion, memory management
│       │   └── memory_caps.py     # ESP32 memory capability flags
│       ├── toolchain/             # Build system
│       │   ├── builder.py         # Main build orchestrator, multi-file discovery
│       │   ├── compiler.py        # GCC wrapper, compilation, linking
│       │   ├── wrapper_generator.py    # Automatic wrapper code generation
│       │   ├── signature_parser.py     # Function signature extraction
│       │   ├── header_generator.py     # C header file generation
│       │   ├── metadata_generator.py   # signature.json generation
│       │   ├── linker_gen.py           # Linker script generation
│       │   ├── binary_processor.py     # Section extraction, BSS padding
│       │   ├── symbol_extractor.py     # Symbol table parsing
│       │   ├── validator.py            # Build validation
│       │   └── binary_object.py        # Binary artifact container
│       ├── templates/
│       │   └── linker.ld.template # Linker script template
│       └── utils/
│           └── logger.py          # Colored logging system
│
├── components/                    # ESP-IDF component (device firmware)
│   └── p4_jit/
│       ├── src/
│       │   ├── p4_jit.c           # Component initialization, task management
│       │   ├── protocol.c         # Binary protocol parser, packet handling
│       │   ├── commands.c         # Command dispatcher (ALLOC, WRITE, EXEC, etc.)
│       │   └── usb_transport.c    # TinyUSB CDC-ACM, StreamBuffer management
│       ├── include/
│       │   └── p4_jit.h           # Public API header
│       ├── Kconfig                # Component configuration options
│       ├── CMakeLists.txt         # ESP-IDF build integration
│       └── sdkconfig.defaults.p4_jit # Default configuration for P4-JIT
│
├── firmware/                      # Example firmware application
│   ├── main/
│   │   └── main.c                 # Minimal firmware (calls p4_jit_start())
│   ├── CMakeLists.txt             # Firmware build script
│   ├── partitions.csv             # Partition table
│   └── sdkconfig.defaults.esp32p4 # ESP32-P4 specific config
│
├── config/                        # Configuration files
│   ├── toolchain.yaml             # ⚠️ CRITICAL: Toolchain paths, compiler flags
│   ├── numpy_types.yaml           # C ↔ NumPy type mapping
│   └── std_types.h                # Standard typedefs for parser
│
├── tests/                         # Example code & test suite
│   └── p4jit/
│       ├── advanced_example/      # Structs, manual memory management
│       ├── bidirectional_sync_example/  # Array sync-back
│       ├── firmware_symbols_example/    # printf, malloc usage
│       ├── heap_info_example/           # Memory statistics
│       ├── simple_logging_example/      # Log level control
│       └── workflow_example/            # Complete workflow, disassembly
│
├── docs/                          # Documentation
│   ├── TRM.md                     # Technical Reference Manual (complete spec)
│   ├── LIMITATIONS.md             # Type system, threading, alignment constraints
│   ├── LIMITATIONS_EXTENDED.md   # L2MEM execution, PMP configuration
│   └── SMART_ARGS.md              # Smart Args detailed documentation
│
└── README.md                      # This file
```

---

## 🎨 Features Deep Dive

### Smart Arguments

Automatic type conversion and memory management:

```python
# NumPy types automatically converted
data = np.array([1, 2, 3], dtype=np.int32)  # Allocates on device
length = np.int32(len(data))
scale = np.float32(2.5)

result = func(data, length, scale)  # Automatic packing/unpacking

# Arrays modified on device are synced back automatically
print(data)  # Shows modified values!
```

### Multi-File Compilation

Automatic discovery and Link-Time Optimization:

```
project/source/
├── main.c
├── helpers.c    # Automatically discovered
└── math.c       # Automatically compiled

# All files linked together with LTO (cross-module inlining)
```

### Symbol Bridge

Call firmware functions with zero overhead:

```c
// Your JIT code
#include <stdio.h>
printf("Hello!");  // Resolved to firmware's printf at 0x400167a6
```

### Type Safety

Runtime validation prevents errors:

```python
# This will fail with clear error
func(10, 20)  # ✗ Python int not allowed

# This works
func(np.int32(10), np.int32(20))  # ✓ Explicit type
```

### Memory Safety

Host-side bounds checking:

```python
# Prevents device crashes
device.write_memory(0xDEADBEEF, data)  # ✗ Raises PermissionError
```

---

## 📐 Type System Reference

### Supported Types

| C Type | NumPy Type | Size | Range/Notes |
|--------|------------|------|-------------|
| `int8_t` | `np.int8` | 1 byte | -128 to 127 |
| `uint8_t` | `np.uint8` | 1 byte | 0 to 255 |
| `int16_t` | `np.int16` | 2 bytes | -32768 to 32767 |
| `uint16_t` | `np.uint16` | 2 bytes | 0 to 65535 |
| `int32_t` | `np.int32` | 4 bytes | -2³¹ to 2³¹-1 |
| `uint32_t` | `np.uint32` | 4 bytes | 0 to 2³²-1 |
| `float` | `np.float32` | 4 bytes | IEEE 754 single precision |
| `Type*` | `np.ndarray` | 4 bytes | Pointer (any type) |

### Unsupported Types

| Type | Why Not Supported | Workaround |
|------|-------------------|------------|
| `int64_t`, `uint64_t` | 4-byte slot limitation | Split into two `int32_t` |
| `double` | 4-byte slot limitation | Use `float` or split |
| `struct` (return) | RISC-V ABI uses hidden pointer | Use output pointer parameter |

---

## ⚙️ Configuration

### Toolchain Configuration (`config/toolchain.yaml`)

```yaml
toolchain:
  path: "YOUR_TOOLCHAIN_PATH"  # ← UPDATE THIS
  prefix: "riscv32-esp-elf"

compiler:
  arch: "rv32imafc_zicsr_zifencei_xesppie"
  abi: "ilp32f"
  optimization: "O3"           # O0, O1, O2, O3, Os
  flags:
    - "-flto"                  # Link-Time Optimization

linker:
  firmware_elf: "firmware/build/p4_jit_firmware.elf"  # For symbol bridge
```

### Firmware Configuration (`firmware/sdkconfig.defaults.esp32p4`)

Key settings:
```kconfig
# CRITICAL: Enable code execution from data memory
CONFIG_ESP_SYSTEM_PMP_IDRAM_SPLIT=n

# PSRAM
CONFIG_SPIRAM=y
CONFIG_SPIRAM_SPEED_200M=y

# USB
CONFIG_TINYUSB_CDC_ENABLED=y
```

---

## 📖 Documentation

- **[Technical Reference Manual (TRM.md)](docs/TRM.md)** - Complete system specification
- **[Limitations (LIMITATIONS.md)](docs/LIMITATIONS.md)** - Type system, threading, alignment constraints
- **[Extended Limitations (LIMITATIONS_EXTENDED.md)](docs/LIMITATIONS_EXTENDED.md)** - L2MEM execution, PMP
- **[Smart Args Guide (SMART_ARGS.md)](docs/SMART_ARGS.md)** - Detailed Smart Args documentation

---

## 🔧 Troubleshooting

### "Device not connected"

**Causes**:
- USB cable issue
- Wrong port selected
- Serial port busy (other program using it)

**Solutions**:
1. Check USB cable is data-capable (not charge-only)
2. Close other serial monitors (PuTTY, TeraTerm, Arduino IDE)
3. Try explicit port: `P4JIT(port='COM3')` or `P4JIT(port='/dev/ttyACM0')`

---

### "Compilation failed: command not found"

**Cause**: Toolchain path not configured or ESP-IDF not in PATH

**Solutions**:
1. Verify `config/toolchain.yaml` has correct path
2. Run ESP-IDF export script:
   ```bash
   . $HOME/esp/esp-idf/export.sh  # Linux/macOS
   ```
3. Test: `riscv32-esp-elf-gcc --version`

---

### "Firmware ELF not found"

**Cause**: Symbol bridge enabled but firmware not built

**Solutions**:
1. Build firmware first:
   ```bash
   cd firmware && idf.py build
   ```
2. Or disable symbol bridge:
   ```python
   func = jit.load(..., use_firmware_elf=False)
   ```

---

### "Guru Meditation Error: IllegalInstruction"

**Causes**:
1. Wrong ISA flags (arch mismatch)
2. Cache not synced
3. Code not uploaded properly

**Solutions**:
1. Verify `config/toolchain.yaml` arch matches ESP32-P4
2. Check firmware logs for cache sync messages
3. Re-upload code

---

### "TypeError: Expected NumPy array, got int"

**Cause**: Using Python types instead of NumPy

**Solution**:
```python
# Wrong
func(10, 20)

# Correct
func(np.int32(10), np.int32(20))
```

---

### "Allocation failed"

**Cause**: Insufficient memory

**Solutions**:
1. Check available memory:
   ```python
   jit.get_heap_stats()
   ```
2. Use PSRAM instead of internal SRAM
3. Reduce binary size (lower optimization, remove debug symbols)

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

**Code Style**:
- Python: PEP 8
- C: ESP-IDF style guide
- Clear variable names
- Comprehensive comments

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **Espressif Systems** - ESP-IDF framework and ESP32-P4 hardware
- **TinyUSB Project** - USB stack
- **RISC-V Foundation** - RISC-V ISA specification

---

## 📬 Contact & Support

- **Author**: Billal
- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions

---

**Happy JIT Coding! 🚀**