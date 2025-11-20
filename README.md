# ESP32-P4 JIT - Dynamic Code Loader

Production-grade build system for compiling position-specific RISC-V binaries for ESP32-P4 dynamic code loading with automatic wrapper generation for memory-mapped I/O communication.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
  - [Basic Compilation](#basic-compilation)
  - [Wrapper Generation](#wrapper-generation)
  - [Multi-File Projects](#multi-file-projects)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Memory-Mapped I/O Protocol](#memory-mapped-io-protocol)
- [Architecture](#architecture)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

### Core Build System
- **Standard Compilation**: Uses normal optimization (-O2/-O3) with standard GCC flags
- **Entry Point Specification**: Specify entry point at build time, not in source
- **BSS Padding**: Automatically pads BSS sections for single `memcpy()` loading
- **Template-Based Linker**: Generates custom linker scripts from templates
- **Multi-File Support**: Automatic discovery and compilation of C, C++, and assembly files
- **Comprehensive Validation**: Validates addresses, alignment, and sizes
- **Rich Metadata**: JSON metadata with all addresses and symbols

### Automatic Wrapper Generation (NEW)
- **Function Signature Parsing**: Extracts function signatures from C source files
- **Auto-Generated Headers**: Creates header files with typedefs and declarations
- **Memory-Mapped I/O Wrapper**: Generates wrapper code for argument passing via fixed addresses
- **Type-Safe Communication**: Handles int, float, and pointer types correctly
- **Metadata Generation**: Creates JSON with all memory addresses and types

### Supported Languages
- **C** (`.c`) - Standard C compilation
- **C++** (`.cpp`, `.cc`, `.cxx`) - C++ with proper linking
- **Assembly** (`.S`) - Assembly with C preprocessor support

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Requirements:**
- Python 3.7+
- PyYAML >= 6.0
- pycparser >= 2.21
- ESP-IDF toolchain (RISC-V GCC)

### 2. Configure Toolchain

Edit `config/toolchain.yaml`:

```yaml
toolchain:
  path: "C:/Espressif/tools/riscv32-esp-elf/esp-14.2.0_20241119/riscv32-esp-elf/bin"
```

### 3. Run Example

```bash
cd examples
python example_simple.py
```

---

## Installation

### Prerequisites

**ESP-IDF Installation:**
1. Install ESP-IDF v5.x or later
2. Ensure RISC-V toolchain is in PATH
3. Verify installation:
   ```bash
   riscv32-esp-elf-gcc --version
   ```

**Python Environment:**
```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

### Basic Compilation

Compile a single C function for dynamic loading:

```python
from esp32_loader import Builder

builder = Builder()

binary = builder.build(
    source='sources/my_function.c',
    entry_point='my_function',
    base_address=0x40800000
)

# Save binary
binary.save_bin('output/my_function.bin')
binary.save_metadata('output/metadata.json')

# Inspect
print(f"Entry: 0x{binary.entry_address:08x}")
print(f"Size: {binary.total_size} bytes")
binary.print_sections()
binary.print_symbols()
```

### Wrapper Generation

Automatically generate memory-mapped I/O wrapper for any function:

```python
from esp32_loader import Builder

builder = Builder()

# Automatic wrapper generation
binary = builder.wrapper.build_with_wrapper(
    source='sources/compute.c',
    function_name='compute2',       # Function to wrap
    base_address=0x40800000,        # Code load address
    arg_address=0x50000000          # I/O region for arguments
)

# Generated files:
# - sources/compute.h      (function declaration + typedefs)
# - sources/temp.c         (wrapper code)
# - output/signature.json  (memory layout metadata)
```

**Example Function:**

```c
// compute.c
float compute2(int32_t a, float b, int32_t* c, int8_t d) {
    return (a + b) * counter + c[2] - d;
}
```

**Runtime Usage (ESP32-P4 Main Firmware):**

```c
volatile int32_t *io = (volatile int32_t *)0x50000000;

// Write arguments to memory-mapped region
io[0] = 42;                          // a (int32_t)
io[1] = *(int32_t*)&3.14f;           // b (float, bit reinterpretation)
io[2] = (int32_t)buffer_ptr;         // c (pointer)
io[3] = 5;                           // d (int8_t)

// Call dynamically loaded function
typedef esp_err_t (*wrapper_func_t)(void);
wrapper_func_t call_remote = (wrapper_func_t)0x40800000;
esp_err_t status = call_remote();

// Read result from last slot
float result = *(float*)&io[31];
```

### Multi-File Projects

The builder automatically discovers and compiles all source files in the same directory:

```
sources/
  ├── main.c           # Entry point
  ├── utils.c          # Utility functions
  ├── utils.h          # Header file
  ├── math_ops.cpp     # C++ implementation
  └── vector.S         # Assembly code
```

```python
builder = Builder()

# Automatically compiles ALL files in sources/
binary = builder.build(
    source='sources/main.c',    # Entry file determines directory
    entry_point='main',
    base_address=0x40800000
)
```

---

## Configuration

### Toolchain Configuration (`config/toolchain.yaml`)

```yaml
toolchain:
  path: "path/to/riscv32-esp-elf/bin"
  prefix: "riscv32-esp-elf"
  compilers:
    gcc: "riscv32-esp-elf-gcc"
    g++: "riscv32-esp-elf-g++"
    as: "riscv32-esp-elf-as"

compiler:
  arch: "rv32imafc_zicsr_zifencei_xesppie"  # ESP32-P4 ISA
  abi: "ilp32f"                              # ABI with float support
  optimization: "O3"                         # Optimization level
  flags:
    - "-nostdlib"
    - "-ffreestanding"
    - "-fno-builtin"
    - "-ffunction-sections"
    - "-fdata-sections"
    - "-msmall-data-limit=0"

memory:
  max_size: "128K"      # Maximum binary size
  alignment: 4          # Memory alignment (bytes)

# Wrapper generation settings
wrapper:
  template_file: "temp.c"           # Generated wrapper filename
  wrapper_entry: "call_remote"      # Wrapper function name
  args_array_size: 32               # Argument slots (32 × 4 = 128 bytes)
                                    # Last slot reserved for return value
```

### ISA Extensions Explained

- `rv32imafc`: Base ISA with multiply, atomic, float, compressed instructions
- `zicsr`: Control and Status Register instructions
- `zifencei`: Instruction fence for self-modifying code
- `xesppie`: ESP32-P4 custom Programmable Instruction Extensions

---

## API Reference

### Builder Class

```python
class Builder:
    def __init__(self, config_path='config/toolchain.yaml'):
        """Initialize builder with configuration."""
        
    def build(self, source, entry_point, base_address, 
              optimization=None, output_dir='build'):
        """
        Build position-specific binary.
        
        Args:
            source: Path to entry source file
            entry_point: Entry point function name
            base_address: Load address (int or hex string)
            optimization: Override optimization level
            output_dir: Output directory
            
        Returns:
            BinaryObject: Compiled binary with metadata
        """
```

### WrapperBuilder Class

```python
builder.wrapper.build_with_wrapper(
    source,              # Original source file
    function_name,       # Function to wrap
    base_address,        # Code load address
    arg_address,         # I/O region base address (REQUIRED)
    output_dir='build'   # Output directory
)
```

### BinaryObject Methods

```python
# Properties
binary.data                # Raw binary data (bytes)
binary.total_size          # Total size including BSS
binary.base_address        # Load address
binary.entry_address       # Entry point address
binary.functions           # List of all functions

# Save methods
binary.save_bin(path)           # Save binary file
binary.save_elf(path)           # Save ELF with debug symbols
binary.save_metadata(path)      # Save JSON metadata

# Inspection methods
binary.print_sections()         # Print section table
binary.print_symbols()          # Print symbol table
binary.print_memory_map()       # Visual memory map
binary.disassemble(output)      # Disassemble code

# Utility methods
binary.get_data()                      # Get raw bytes
binary.get_metadata_dict()             # Get metadata as dict
binary.get_function_address(name)      # Get function address
binary.validate()                      # Validate binary
```

---

## Memory-Mapped I/O Protocol

### Memory Layout

```
Base Address: 0x50000000 (configurable)
Array Size: 32 slots × 4 bytes = 128 bytes

Address          Index    Usage
─────────────────────────────────────────
0x50000000       [0]      Argument 0
0x50000004       [1]      Argument 1
0x50000008       [2]      Argument 2
0x5000000c       [3]      Argument 3
...
0x50000078       [30]     Argument 30
0x5000007c       [31]     RETURN VALUE (last slot)
```

### Type Handling

**Value Types (int, float):**
```c
// Write
io[0] = 42;                          // int32_t
io[1] = *(int32_t*)&3.14f;           // float (reinterpret bits)

// Read
int32_t x = io[0];
float y = *(float*)&io[1];
```

**Pointer Types:**
```c
// Write
io[2] = (int32_t)buffer_ptr;         // Cast pointer to int

// Read
int32_t* ptr = (int32_t*)io[2];      // Cast int to pointer
```

### signature.json Format

```json
{
  "function": {
    "name": "compute2",
    "return_type": "float",
    "wrapper_entry": "call_remote"
  },
  "addresses": {
    "code_base": "0x40800000",
    "arg_base": "0x50000000",
    "args_array_size": 32,
    "args_array_bytes": 128
  },
  "arguments": [
    {
      "index": 0,
      "name": "a",
      "type": "int32_t",
      "category": "value",
      "address": "0x50000000"
    }
  ],
  "result": {
    "type": "float",
    "index": 31,
    "address": "0x5000007c"
  }
}
```

---

## Architecture

### Directory Structure

```
P4-JIT/
├── config/
│   └── toolchain.yaml              # Build configuration
├── esp32_loader/                   # Main package
│   ├── __init__.py
│   ├── builder.py                  # Build orchestrator
│   ├── compiler.py                 # Compilation & linking
│   ├── linker_gen.py               # Linker script generator
│   ├── binary_processor.py         # Section extraction & BSS padding
│   ├── symbol_extractor.py         # Symbol table parsing
│   ├── validator.py                # Input validation
│   ├── binary_object.py            # Result object API
│   ├── signature_parser.py         # C function signature parser
│   ├── header_generator.py         # Header file generator
│   ├── wrapper_generator.py        # Wrapper code generator
│   ├── wrapper_builder.py          # Wrapper build orchestrator
│   └── metadata_generator.py       # JSON metadata generator
├── templates/
│   └── linker.ld.template          # Linker script template
├── test/
│   ├── test_single_file/           # Single file compilation test
│   ├── test_multi_file/            # Multi-file compilation test
│   └── test_wrapper/               # Wrapper generation test
├── examples/
│   ├── example_simple.py           # Basic usage example
│   └── sources/
│       └── compute.c               # Example source
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

### Build Flow

**Basic Compilation:**
```
1. Load configuration
2. Validate inputs (source, entry point, address)
3. Discover source files in directory
4. Compile each file → object files
5. Generate linker script
6. Link object files → ELF
7. Extract binary sections
8. Pad BSS with zeros
9. Extract symbols and addresses
10. Return BinaryObject
```

**Wrapper Generation:**
```
1. Parse function signature (pycparser)
2. Extract typedefs from source
3. Generate header file (.h)
4. Generate wrapper code (temp.c)
5. Compile wrapper + original source
6. Link (no duplicate symbols)
7. Generate signature.json
8. Return BinaryObject
```

---

## Examples

### Example 1: Simple Function

```c
// sources/add.c
int32_t add(int32_t a, int32_t b) {
    return a + b;
}
```

```python
from esp32_loader import Builder

builder = Builder()
binary = builder.build(
    source='sources/add.c',
    entry_point='add',
    base_address=0x40800000
)

binary.save_bin('output/add.bin')
```

### Example 2: Function with Wrapper

```c
// sources/filter.c
float lowpass_filter(float input, float cutoff, float* state) {
    *state = *state * (1.0f - cutoff) + input * cutoff;
    return *state;
}
```

```python
from esp32_loader import Builder

builder = Builder()
binary = builder.wrapper.build_with_wrapper(
    source='sources/filter.c',
    function_name='lowpass_filter',
    base_address=0x40800000,
    arg_address=0x50000000
)

# Generated: filter.h, temp.c, signature.json
binary.save_bin('output/filter.bin')
```

### Example 3: Multi-File Project

```c
// sources/main.c
#include "dsp.h"

void process_audio(float* buffer, int size) {
    for (int i = 0; i < size; i++) {
        buffer[i] = apply_filter(buffer[i]);
    }
}
```

```c
// sources/dsp.c
#include "dsp.h"

float apply_filter(float sample) {
    // DSP implementation
    return sample * 0.5f;
}
```

```python
builder = Builder()
binary = builder.build(
    source='sources/main.c',  # Entry file
    entry_point='process_audio',
    base_address=0x40800000
)
# Automatically compiles main.c and dsp.c
```

---

## Troubleshooting

### Import Error

**Problem:** `ModuleNotFoundError: No module named 'esp32_loader'`

**Solution:** Ensure you're in the correct directory or add to path:
```python
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
```

### Toolchain Not Found

**Problem:** Compilation fails with toolchain errors

**Solutions:**
1. Verify ESP-IDF installation
2. Check toolchain path in `config/toolchain.yaml`
3. Run from ESP-IDF environment:
   - Windows: ESP-IDF Command Prompt
   - Linux: `source ~/esp/esp-idf/export.sh`

### Entry Point Not Found

**Problem:** `Entry point 'function_name' not found in compiled binary`

**Solutions:**
1. Verify function name matches exactly
2. Ensure function is not `static`
3. Check function isn't optimized away (use `__attribute__((used))`)

### Duplicate Symbol Error

**Problem:** `multiple definition of 'function_name'`

**Cause:** Wrapper system includes source file, and builder also compiles it

**Solution:** This is automatically handled by header generation. If you see this error:
1. Delete old `temp.c` files
2. Ensure you're using the latest wrapper generator
3. Check that generated header exists

### Memory Alignment Error

**Problem:** `Address 0xXXXXXXXX not 4-byte aligned`

**Solution:** Use addresses divisible by 4:
- ✓ `0x40800000`
- ✓ `0x40800004`
- ✗ `0x40800003` (not aligned)

### Arguments Exceed Array Size

**Problem:** `Function has X parameters but args array supports max Y arguments`

**Solution:** Increase `args_array_size` in config:
```yaml
wrapper:
  args_array_size: 64  # Increase from 32 to 64
```

---

## Performance Notes

### Binary Size
- Typical wrapper overhead: ~30-40 bytes
- Memory-mapped I/O: ~14 bytes overhead
- Total wrapper size: ~100-200 bytes (depends on arg count)

### Execution Speed
- Wrapper overhead: ~10-20 CPU cycles
- Memory access latency: 4-16 cycles (cached vs uncached)
- Total overhead: ~30-50 cycles per call

### Optimization Tips
1. Use `-O3` for maximum performance
2. Keep functions in same translation unit when possible
3. Use `inline` for small wrapper functions
4. Align memory-mapped regions to cache lines

---

## License

MIT License

Copyright (c) 2025 BoumedineBillal

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
