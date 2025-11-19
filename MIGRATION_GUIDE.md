# Migration Guide: Single-File to Multi-File System

## Good News: No Migration Needed!

The multi-file system is **100% backward compatible**. Your existing code continues to work without any changes.

## What Changed (Internally)

### Configuration File
New sections added to `config/toolchain.yaml`, but existing sections unchanged.

### API
No changes to the public API:
```python
# This still works exactly as before
builder = Builder()
binary = builder.build(
    source='compute.c',
    entry_point='compute',
    base_address=0x40800000
)
```

## New Capability: Automatic Multi-File Compilation

If you place multiple source files in the same directory, they are automatically compiled and linked together.

### Example: Converting Single File to Multi-File

**Before (single file):**
```
sources/
  └── compute.c  (contains all code)
```

**After (multi-file):**
```
sources/
  ├── compute.c   (entry point)
  ├── utils.c     (utility functions)
  ├── utils.h     (header file)
  └── math.cpp    (C++ math functions)
```

**Same build command:**
```python
builder = Builder()
binary = builder.build(
    source='sources/compute.c',  # Entry file
    entry_point='compute',
    base_address=0x40800000
)
```

All files in `sources/` are automatically discovered, compiled, and linked.

## File Organization Tips

### Keep Everything in One Directory
```
my_project/
  ├── main.c
  ├── dsp.c
  ├── dsp.h
  ├── vector.S
  └── utils.cpp
```

### Headers Are Automatically Found
```c
// In main.c:
#include "dsp.h"      // Works automatically
#include "utils.hpp"  // Works automatically
```

### C++ Files Need extern "C"
```cpp
// In utils.cpp:
extern "C" {
    int my_function(int x);  // Callable from C
}
```

## Supported File Types

| Extension | Language | Compiler |
|-----------|----------|----------|
| `.c` | C | gcc |
| `.cpp` | C++ | g++ |
| `.cc` | C++ | g++ |
| `.cxx` | C++ | g++ |
| `.S` | Assembly (with preprocessor) | gcc |
| `.s` | Assembly (pure) | as |

## Testing Your Migration

### Test 1: Verify Single-File Still Works
```bash
cd test/test_single_file
python test_single.py
```

### Test 2: Try Multi-File Example
```bash
cd test/test_multi_file
python test_multi.py
```

## Common Questions

### Q: Do I need to update my existing projects?
**A:** No. Everything works as before.

### Q: What if I have only one source file?
**A:** It works exactly as before. The builder just finds one file and compiles it.

### Q: Can I mix C and C++?
**A:** Yes. Use `extern "C"` in C++ for functions called from C.

### Q: Where do I put header files?
**A:** Same directory as source files. They're automatically found via `-I` flag.

### Q: Can I use subdirectories?
**A:** No. All files must be in the same directory as the entry file.

### Q: How do I know which files will be compiled?
**A:** The builder prints all discovered files before compilation.

## Summary

- **No breaking changes**
- **No API changes**
- **Automatic multi-file support**
- **Backward compatible**
- **Same usage pattern**

Your existing code continues to work. New multi-file projects benefit from automatic discovery and compilation.
