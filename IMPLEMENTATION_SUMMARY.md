# Multi-File Compilation System - Implementation Summary

## Changes Made

### 1. Configuration File (`config/toolchain.yaml`)

**Added:**
- `toolchain.compilers` section mapping compiler names to executables
- `extensions.compile` section mapping file extensions to compilers
- `extensions.headers` section listing header file extensions
- Comments explaining ISA extensions

**Extension to Compiler Mapping:**
```yaml
extensions:
  compile:
    ".c": "gcc"       # C source files
    ".cpp": "g++"     # C++ source files
    ".cc": "g++"      # C++ alternative
    ".cxx": "g++"     # C++ alternative
    ".S": "gcc"       # Assembly with preprocessor
    ".s": "as"        # Pure assembly
```

### 2. Compiler Module (`esp32_loader/compiler.py`)

**Changed `__init__`:**
- Builds compiler paths from config (`gcc`, `g++`, `as`)
- Stores in `self.compilers` dictionary

**Changed `compile()` signature:**
- Removed `include_dirs` parameter (derived automatically from source file)
- Now: `compile(self, source, output, optimization='O2')`

**New logic in `compile()`:**
1. Extracts file extension from source
2. Looks up compiler from config
3. Automatically derives include directory from source file location
4. Selects compilation flags based on compiler type (`as` vs `gcc`/`g++`)
5. Adds `-I` flag pointing to source directory

**Changed `link()` signature:**
- Now accepts list of object files: `link(self, obj_files, linker_script, output)`
- Expands list into subprocess command

### 3. Builder Module (`esp32_loader/builder.py`)

**Added import:**
- `import glob` for file discovery

**New method `_discover_source_files()`:**
- Scans directory for all files matching configured extensions
- Returns sorted list for deterministic builds

**Changed `build()` method:**
1. Derives source directory from entry file path
2. Discovers all compilable files in directory
3. Compiles each file to unique object file in temp directory
4. Passes all object files to linker
5. Prints progress for each compilation step

**Build flow:**
```
Entry file → Source directory → Discover all sources → 
Compile each → Link all → Extract binary
```

### 4. Test Structure

**Created `test/` directory with two tests:**

**Test 1: `test_single_file/`**
- Single C file
- Validates backward compatibility
- Ensures existing code still works

**Test 2: `test_multi_file/`**
- Multiple source files (C, C++, Assembly)
- Validates multi-file compilation
- Tests cross-language linking

## Key Features

### Automatic File Discovery
- Builder scans source directory
- Compiles all files matching configured extensions
- No need to specify each file

### Extension-Based Compiler Selection
- Configuration file maps extensions to compilers
- Easily extensible for new file types
- No hardcoded logic in Python

### Automatic Include Paths
- Include directory derived from source file location
- Headers in same directory are automatically found
- Simple `-I` flag pointing to source directory

### Deterministic Builds
- Files sorted alphabetically before compilation
- Same input always produces same output
- Reproducible builds

### Progress Feedback
- Prints discovered files
- Shows compilation progress for each file
- Clear success/failure indicators

## Backward Compatibility

The system maintains full backward compatibility:
- Single-file projects work exactly as before
- API unchanged: `build(source, entry_point, base_address)`
- Existing examples still run without modification

## Testing

### Run Single File Test
```bash
cd test/test_single_file
python test_single.py
```

### Run Multi-File Test
```bash
cd test/test_multi_file
python test_multi.py
```

## File Type Support

| Extension | Compiler | Description |
|-----------|----------|-------------|
| `.c` | gcc | C source files |
| `.cpp` | g++ | C++ source files |
| `.cc` | g++ | C++ source (alternative) |
| `.cxx` | g++ | C++ source (alternative) |
| `.S` | gcc | Assembly with C preprocessor |
| `.s` | as | Pure assembly (no preprocessor) |

## Example Usage

### Single File (Backward Compatible)
```python
builder = Builder()
binary = builder.build(
    source='sources/main.c',
    entry_point='main',
    base_address=0x40800000
)
```

### Multi-File (Automatic)
```python
# Directory structure:
# sources/
#   ├── main.c
#   ├── utils.c
#   ├── utils.h
#   └── math.cpp

builder = Builder()
binary = builder.build(
    source='sources/main.c',  # Entry file determines directory
    entry_point='main',
    base_address=0x40800000
)
# Automatically compiles ALL files in sources/
```

## Technical Details

### Include Path Resolution
```c
// In any source file:
#include "utils.h"  // Found via -I pointing to source directory
```

### Cross-Language Linking
```cpp
// C++ file (math.cpp)
extern "C" {
    int compute(int a, int b);  // C linkage for C compatibility
}
```

### Assembly Integration
```asm
// vector.S
.global vector_add
vector_add:
    add a0, a0, a1
    ret
```

## Configuration Flexibility

Add new file types in `toolchain.yaml`:
```yaml
extensions:
  compile:
    ".rs": "rustc"    # Example: Rust support
    ".zig": "zig"     # Example: Zig support
```

## Error Handling

Clear error messages for:
- Unknown file extensions
- Compilation failures per file
- Missing entry point
- No source files found

## Performance

- Parallel compilation possible (future enhancement)
- Deterministic object file naming
- Efficient temp directory usage
