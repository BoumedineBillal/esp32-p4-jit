# Quick Start Guide

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Verify Toolchain Path

Edit `config/toolchain.yaml` and ensure the toolchain path is correct:

```yaml
toolchain:
  path: "C:/Espressif/tools/riscv32-esp-elf/esp-14.2.0_20241119/riscv32-esp-elf/bin"
```

## Step 3: Run Example

```bash
cd examples
python example_simple.py
```

Expected output:
```
ESP32-P4 Dynamic Code Loader - Simple Example
============================================================

Building: sources/compute.c
Entry point: compute
Base address: 0x40800000

✓ Build successful!
  Entry point: 0x40800000
  Total size: 184 bytes

...
```

## Step 4: Check Output

The example creates an `output/` directory with:
- `compute.bin` - Binary ready to load to ESP32-P4
- `compute.elf` - ELF file with debug symbols
- `metadata.json` - JSON with all addresses and sizes

## Step 5: Use in Your Code

Create your own Python script:

```python
from esp32_loader import Builder

builder = Builder()

binary = builder.build(
    source='my_function.c',
    entry_point='my_function',
    base_address=0x40800000
)

# Use the binary
data = binary.get_data()
print(f"Size: {binary.total_size} bytes")
print(f"Entry: 0x{binary.entry_address:08x}")

# Save for loading
binary.save_bin('my_function.bin')
```

## Troubleshooting

### Import Error

If you get `ModuleNotFoundError: No module named 'esp32_loader'`:

Make sure you're running from the correct directory or adjust Python path:

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
```

### Toolchain Not Found

If you get toolchain errors, verify:
1. ESP-IDF is installed
2. Toolchain path in `config/toolchain.yaml` is correct
3. Run from ESP-IDF command prompt (Windows) or source export.sh (Linux)

### Entry Point Not Found

If entry point is not found, ensure:
1. Function name matches exactly
2. Function is not static
3. Function is compiled (not optimized away)

## Next Steps

1. Read `README.md` for full documentation
2. Explore `BinaryObject` methods
3. Create your own C functions
4. Integrate with ESP32-P4 loader code
