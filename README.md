# ESP32-P4 Dynamic Code Loader

Production-grade build system for compiling position-specific RISC-V binaries for ESP32-P4 dynamic code loading.

## Features

- **Standard Compilation**: Uses normal optimization (-O2 by default), no KEEP() directives
- **Entry Point Specification**: Specify entry point at build time, not in source
- **BSS Padding**: Automatically pads BSS sections into binary for single memcpy() loading
- **Template-Based Linker**: Generates custom linker scripts from template
- **YAML Configuration**: All toolchain paths and flags in config file
- **Python API**: Simple, programmatic interface
- **Comprehensive Validation**: Validates addresses, alignment, sizes
- **Rich Metadata**: JSON metadata with all addresses and symbols

## Directory Structure

```
f3_function_standar_binary/
├── config/
│   └── toolchain.yaml          # Toolchain configuration
├── esp32_loader/              # Main package
│   ├── __init__.py
│   ├── builder.py             # Main orchestrator
│   ├── compiler.py            # Compile & link
│   ├── linker_gen.py          # Linker script generator
│   ├── binary_processor.py    # Section extraction & BSS padding
│   ├── symbol_extractor.py    # Symbol table parsing
│   ├── validator.py           # Input validation
│   └── binary_object.py       # Result object with methods
├── templates/
│   └── linker.ld.template     # Linker script template
├── examples/
│   ├── example_simple.py      # Simple usage example
│   └── sources/
│       └── compute.c          # Example C source
└── requirements.txt
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure toolchain path in `config/toolchain.yaml`

## Usage

### Simple Example

```python
from esp32_loader import Builder

builder = Builder()

binary = builder.build(
    source='sources/compute.c',
    entry_point='compute',
    base_address=0x40800000
)

# Access properties
print(f"Entry: 0x{binary.entry_address:08x}")
print(f"Size: {binary.total_size} bytes")

# Save outputs
binary.save_bin('output/compute.bin')
binary.save_metadata('output/metadata.json')

# Inspect
binary.print_sections()
binary.print_symbols()

# Get raw data
data = binary.get_data()
```

### Run Example

```bash
cd examples
python example_simple.py
```

## Configuration

Edit `config/toolchain.yaml` to match your environment:

```yaml
toolchain:
  path: "C:/Espressif/tools/riscv32-esp-elf/esp-14.2.0_20241119/riscv32-esp-elf/bin"
  
compiler:
  optimization: "O2"
  
memory:
  max_size: "128K"
```

## BinaryObject Methods

The `build()` method returns a `BinaryObject` with these methods:

**Properties:**
- `.data` - Raw binary as bytes
- `.total_size` - Total size including BSS
- `.base_address` - Load address
- `.entry_address` - Entry point address
- `.functions` - List of all functions

**Save methods:**
- `.save_bin(path)` - Save binary file
- `.save_elf(path)` - Save ELF file
- `.save_metadata(path)` - Save JSON metadata

**Inspection methods:**
- `.print_sections()` - Print section table
- `.print_symbols()` - Print symbol table
- `.print_memory_map()` - Visual memory map
- `.disassemble(output)` - Disassemble code

**Utility methods:**
- `.get_data()` - Get raw bytes
- `.get_metadata_dict()` - Get metadata dict
- `.get_function_address(name)` - Get function address
- `.validate()` - Validate binary

## Key Features Explained

### No KEEP() Directives

Uses standard `-ffunction-sections` and `--gc-sections` with proper entry point specification.

### BSS Padding

Binary includes zeros for BSS sections:
```
[.text][.rodata][.data][.bss padding (zeros)]
```

Load with single `memcpy()` - no separate BSS zeroing needed.

### Optimization Enabled

Compiles with `-O2` by default for production performance.

### Small Data Sections Disabled

Uses `-msmall-data-limit=0` to eliminate `.sdata`, `.sbss`, `.srodata` for simpler memory layout.

## Example Output

```
ESP32-P4 Dynamic Code Loader - Simple Example
============================================================

Building: sources/compute.c
Entry point: compute
Base address: 0x40800000

✓ Build successful!
  Entry point: 0x40800000
  Total size: 184 bytes

Sections:
  .text                0x40800000     132 bytes
  .rodata              0x40800084      16 bytes
  .data                0x40800094       4 bytes
  .bss                 0x40800098       4 bytes

Functions:
  compute                        0x40800000   100 bytes
  get_call_count                 0x40800064    26 bytes
  get_total_sum                  0x4080007e    26 bytes

Memory Map (Base: 0x40800000):
  ────────────────────────────────────────────────────────────
       0  │ .text           132 bytes
     132  │ .rodata          16 bytes
     148  │ .data             4 bytes
     152  │ .bss              4 bytes
  ────────────────────────────────────────────────────────────
  Total: 156 bytes
```

## License

MIT License
