# Wrapper Generation Test

This test demonstrates the automatic wrapper generation feature of the ESP32-P4 JIT system.

## Test Function

```c
float compute2(int32_t a, float b, int32_t* c, int8_t d) {
    counter++;
    return (a + b) * counter + c[2] - d;
}
```

**Parameters:**
- `a`: VALUE type (int32_t)
- `b`: VALUE type (float)
- `c`: POINTER type (int32_t*)
- `d`: VALUE type (int8_t)

**Return:** float

## Running the Test

```bash
cd test/test_wrapper
python test_wrapper.py
```

## What the Test Does

1. **Parses** the function signature from `test_func.c`
2. **Generates** `temp.c` wrapper with memory-mapped I/O
3. **Builds** the wrapper using existing builder
4. **Generates** `signature.json` with all addresses
5. **Saves** binary and metadata

## Expected Output

**Generated Files:**

- `sources/temp.c` - Auto-generated wrapper code
- `output/wrapped.bin` - Binary ready for ESP32-P4
- `output/wrapped.elf` - ELF with debug symbols
- `output/metadata.json` - Build metadata
- `output/signature.json` - Function signature with addresses

## Memory Layout

**Args array:** 32 slots (128 bytes) at 0x50000000

```
0x50000000  [0]   arg 0 (a: int32_t)
0x50000004  [1]   arg 1 (b: float)
0x50000008  [2]   arg 2 (c: int32_t*)
0x5000000c  [3]   arg 3 (d: int8_t)
...
0x5000007c  [31]  RETURN VALUE (float)
```

## signature.json Example

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
    },
    ...
  ],
  "result": {
    "type": "float",
    "index": 31,
    "address": "0x5000007c"
  }
}
```

## Runtime Usage

On ESP32-P4 main firmware:

```c
volatile int32_t *io = (volatile int32_t *)0x50000000;

// Write arguments
io[0] = 42;                          // a (int32_t)
io[1] = *(int32_t*)&3.14f;           // b (float bits)
io[2] = (int32_t)buffer_ptr;         // c (pointer)
io[3] = 5;                           // d (int8_t)

// Call wrapper
typedef esp_err_t (*wrapper_func_t)(void);
wrapper_func_t call_remote = (wrapper_func_t)0x40800000;
call_remote();

// Read result from last slot
float result = *(float*)&io[31];
```
