# Multi-File Compilation Test

This test demonstrates the multi-file compilation capability of the ESP32-P4 Dynamic Code Loader.

## Test Structure

```
test_multi_file/
├── sources/
│   ├── main.c          # Entry point (C file)
│   ├── utils.c         # Utility functions (C file)
│   ├── utils.h         # Header file
│   ├── math_ops.cpp    # C++ implementation
│   └── vector.S        # Assembly with preprocessor
├── output/             # Build outputs (generated)
└── test_multi.py       # Test script
```

## What This Test Validates

1. **Multi-file discovery**: Builder scans directory and finds all source files
2. **C compilation**: Compiles `.c` files with gcc
3. **C++ compilation**: Compiles `.cpp` files with g++
4. **Assembly**: Compiles `.S` files (with preprocessor) using gcc
5. **Header inclusion**: Headers are found via `-I` flag pointing to source directory
6. **Linking**: All object files are linked together into single binary
7. **Cross-language linking**: C, C++, and assembly code work together

## Running the Test

```bash
cd test/test_multi_file
python test_multi.py
```

## Expected Output

```
======================================================================
ESP32-P4 Multi-File Compilation Test
======================================================================

Entry file: main.c
Entry point: main
Base address: 0x40800000

Discovered 4 source file(s):
  - main.c
  - math_ops.cpp
  - utils.c
  - vector.S
Compiling main.c... ✓
Compiling math_ops.cpp... ✓
Compiling utils.c... ✓
Compiling vector.S... ✓
Linking 4 object file(s)... ✓

======================================================================
✓ Build successful!
======================================================================
```

## Files Generated

- `output/multi.bin` - Binary ready for ESP32-P4
- `output/multi.elf` - ELF file with debug symbols
- `output/metadata.json` - Function addresses and metadata

## Notes

- All source files must be in the same directory
- Headers are automatically found via include path
- File compilation order is deterministic (alphabetical)
- C++ functions use `extern "C"` for C linkage
