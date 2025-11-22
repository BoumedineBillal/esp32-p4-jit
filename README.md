# ESP32-P4 JIT: The Complete Technical Manual

**Version**: 1.0.0
**Target Architecture**: RISC-V (ESP32-P4)
**License**: MIT

---

## 📖 Table of Contents

1.  [Executive Summary](#1-executive-summary)
2.  [System Architecture](#2-system-architecture)
    *   [2.1 Host Build System (`esp32_loader`)](#21-host-build-system-esp32_loader)
    *   [2.2 Host Runtime (`p4_jit`)](#22-host-runtime-p4_jit)
    *   [2.3 Device Firmware (`p4_jit_firmware`)](#23-device-firmware-p4_jit_firmware)
3.  [The JIT Workflow (The "Two-Pass" Mechanism)](#3-the-jit-workflow-the-two-pass-mechanism)
4.  [Installation & Setup](#4-installation--setup)
5.  [Usage Guide](#5-usage-guide)
    *   [5.1 Hello World](#51-hello-world)
    *   [5.2 Working with Arrays](#52-working-with-arrays)
6.  [API Reference](#6-api-reference)
7.  [Communication Protocol Specification](#7-communication-protocol-specification)
8.  [Internals & Design Decisions](#8-internals--design-decisions)
    *   [8.1 Why Position Specific Code?](#81-why-position-specific-code)
    *   [8.2 Automatic ABI Wrapping](#82-automatic-abi-wrapping)
    *   [8.3 Cache Coherency & Safety](#83-cache-coherency--safety)
9.  [Troubleshooting](#9-troubleshooting)

---

## 1. Executive Summary

The **ESP32-P4 JIT** is a sophisticated dynamic code loading system designed for the ESP32-P4 microcontroller. It enables developers to compile C/C++ code on a host PC and execute it natively on the ESP32-P4 without flashing the main firmware.

Unlike interpreted languages (MicroPython, Lua) or bytecode VMs (WASM), this system executes **native, optimized RISC-V machine code**. This ensures maximum performance, making it suitable for computationally intensive tasks like Digital Signal Processing (DSP), cryptography, or real-time control loops.

The system handles the entire lifecycle of dynamic execution:
1.  **Cross-Compilation**: Using the standard ESP-IDF RISC-V toolchain.
2.  **Linking**: Generating position-specific binaries for runtime-allocated memory.
3.  **Transport**: High-speed USB transfer.
4.  **Execution**: Safe invocation of code with automatic cache management.

---

## 2. System Architecture

The project follows a client-server model, split across the Host (PC) and the Device (ESP32-P4).

### 2.1 Host Build System (`esp32_loader`)
This is the "Compiler Driver". It is a Python package responsible for transforming C source code into a raw binary blob ready for the device.

*   **`Builder`**: The central orchestrator. It manages the build pipeline.
*   **`Compiler`**: Wraps `riscv32-esp-elf-gcc`. It handles flag management (`-march`, `-mabi`, `-O3`) to ensure the binary is compatible with the P4's hardware.
*   **`WrapperGenerator`**: A critical component that solves the ABI (Application Binary Interface) problem. It parses the user's C code using `pycparser`, extracts function signatures, and generates a C wrapper (`temp.c`). This wrapper reads arguments from a fixed memory buffer, casts them to the correct types, calls the user function, and writes the result back.
*   **`LinkerGenerator`**: Dynamically creates GNU Linker scripts (`.ld`). It takes a base address as input and generates a script that links the code to run *specifically* at that address.
*   **`BinaryProcessor`**: Extracts the `.text`, `.data`, and `.rodata` sections from the compiled ELF file. Crucially, it also handles `.bss` (uninitialized data) by appending zero-padding to the binary, ensuring that global variables are correctly initialized when loaded.

### 2.2 Host Runtime (`p4_jit`)
This is the "Client Library". It manages the connection to the device and the logic of the JIT session.

*   **`DeviceManager`**: Implements the custom binary protocol over USB Serial (CDC-ACM). It maintains a **Shadow Allocation Table** on the host. This table tracks every memory region allocated on the device. If the user tries to write to or execute an address that wasn't allocated, the `DeviceManager` blocks the request locally, preventing segmentation faults or crashes on the embedded device.
*   **`JITSession`**: Provides the high-level API. It abstracts the connection process (auto-discovery via `PING`) and the function loading process.

### 2.3 Device Firmware (`p4_jit_firmware`)
This is the "Server". It is a specialized ESP-IDF application running on the ESP32-P4.

*   **USB Transport**: Built on top of **TinyUSB**. It uses FreeRTOS StreamBuffers to decouple the high-priority USB Interrupt Service Routine (ISR) from the lower-priority protocol task. This ensures that even if the protocol task is busy, incoming USB data is buffered and not lost.
*   **Command Dispatcher**: Parses incoming packets and executes commands (`ALLOC`, `WRITE`, `EXEC`).
*   **Memory Manager**: Wraps `heap_caps_aligned_alloc` to provide memory from specific regions (PSRAM vs SRAM) with specific capabilities (Executable, DMA-capable, etc.).

---

## 3. The JIT Workflow (The "Two-Pass" Mechanism)

A fundamental challenge in dynamic loading is **Address Resolution**. When code is compiled, jumps and data references must point to valid memory addresses.
*   **Static Linking**: Addresses are known at compile time (standard firmware).
*   **Position Independent Code (PIC)**: Addresses are calculated relative to the Program Counter (PC). This is complex on embedded systems (requires GOT/PLT).
*   **Position Specific Code**: Code is linked for a specific address. This is efficient but requires knowing the address *before* linking.

We chose **Position Specific Code** for performance and simplicity. This necessitates a **Two-Pass Workflow**:

### Phase 1: The Probe (Discovery)
1.  **Compile**: The host compiles the code using a **Dummy Address** (e.g., `0x00000000`).
2.  **Measure**: The resulting binary is invalid for execution, but its **Size** is correct. We extract:
    *   `Code Size`: Total size of instructions + data + BSS.
    *   `Args Size`: Size needed for the argument passing buffer.

### Phase 2: Allocation (Reservation)
1.  **Request**: The host sends an `ALLOC` command to the device for the measured sizes.
2.  **Allocate**: The device allocates memory in the requested region (e.g., PSRAM).
3.  **Return**: The device returns the **Physical Addresses** (e.g., Code=`0x40081234`, Args=`0x3FC05678`).

### Phase 3: The Final Build (Linking)
1.  **Re-Compile**: The host recompiles the *exact same source*.
2.  **Link**: The `LinkerGenerator` creates a script with `ORIGIN = 0x40081234`.
3.  **Output**: The linker resolves all symbols relative to `0x40081234`. The binary is now valid.

### Phase 4: Execution (Runtime)
1.  **Upload**: The host writes the binary to `0x40081234`.
2.  **Execute**: The host sends an `EXEC` command. The device jumps to `0x40081234`.

---

## 4. Installation & Setup

### Prerequisites
*   **Hardware**: ESP32-P4 Development Board.
*   **OS**: Windows, Linux, or macOS.
*   **Software**:
    *   Python 3.7+
    *   ESP-IDF v5.x (must include RISC-V toolchain).

### Step 1: Host Setup
1.  Clone the repository.
2.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Configure the toolchain in `config/toolchain.yaml`:
    ```yaml
    toolchain:
      path: "C:/Espressif/tools/riscv32-esp-elf/esp-13.2.0_20230928/riscv32-esp-elf/bin"
      prefix: "riscv32-esp-elf"
    ```

### Step 2: Device Setup
1.  Navigate to the firmware directory:
    ```bash
    cd p4_jit_firmware
    ```
2.  Set the target:
    ```bash
    idf.py set-target esp32p4
    ```
3.  Build and Flash:
    ```bash
    idf.py build flash monitor
    ```
    *Note: Keep the monitor open to see debug logs from the device.*

---

## 5. Usage Guide

### 5.1 Hello World (Simple Calculation)

```python
from esp32_loader import Builder
from p4_jit import JITSession
from p4_jit.memory_caps import MALLOC_CAP_SPIRAM, MALLOC_CAP_8BIT
import struct

# 1. Connect
session = JITSession()
session.connect()

# 2. Create Source
with open("math.c", "w") as f:
    f.write("int add(int a, int b) { return a + b; }")

# 3. Probe (Pass 1)
builder = Builder()
temp_bin = builder.wrapper.build_with_wrapper(
    source="math.c", function_name="add",
    base_address=0, arg_address=0
)

# 4. Allocate
# Code needs EXEC capability. Args need DATA capability.
code_addr = session.device.allocate(temp_bin.total_size + 64, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT, 128)
args_addr = session.device.allocate(128, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT, 128)

# 5. Final Build (Pass 2)
final_bin = builder.wrapper.build_with_wrapper(
    source="math.c", function_name="add",
    base_address=code_addr, arg_address=args_addr
)

# 6. Upload & Load
remote_func = session.load_function(final_bin, args_addr)

# 7. Execute
# Pack arguments: two integers (4 bytes each)
args = struct.pack("<ii", 10, 20)
remote_func(args)

# 8. Read Result
# Result is always at the last 4 bytes of the args buffer (slot 31)
res_bytes = session.device.read_memory(args_addr + 124, 4)
result = struct.unpack("<i", res_bytes)[0]
print(f"10 + 20 = {result}")
```

### 5.2 Working with Arrays

Passing pointers requires allocating the data buffer on the device first.

```python
# 1. Prepare Data
data = [1, 2, 3, 4]
data_bytes = struct.pack("<4i", *data)

# 2. Allocate Data Buffer
data_addr = session.device.allocate(len(data_bytes), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT, 128)
session.device.write_memory(data_addr, data_bytes)

# 3. Compile Function
# int sum(int *arr, int len) { ... }
# ... (Two-Pass Build omitted for brevity) ...

# 4. Call
# Pass the POINTER (address) and LENGTH
args = struct.pack("<Ii", data_addr, 4)
remote_func(args)
```

### 5.3 Smart Args (NumPy Support)

The **Smart Args** feature automates type checking, memory allocation, and return value conversion using NumPy.

**Prerequisites**:
*   `numpy` installed.
*   `smart_args=True` passed to `load_function`.

**Usage**:
```python
import numpy as np

# 1. Load Function with Smart Args
remote_func = session.load_function(final_bin, args_addr, smart_args=True)

# 2. Prepare NumPy Data (Strict Types Required)
# You MUST use specific NumPy types (np.int32, np.float32, etc.)
# Standard Python int/float are NOT allowed to prevent ambiguity.
data = np.array([1, 2, 3, 4], dtype=np.int32)
length = np.int32(4)

# 3. Call Directly
# Returns a NumPy scalar (e.g., np.int32)
result = remote_func(data, length)

print(f"Result: {result}")
```

**Configuration**:
Map NumPy types to C types in `config/numpy_types.yaml`.

---

### 5.4 Multi-file Compilation & Optimization

The builder automatically discovers and compiles all source files in the same directory as the entry file.

**Multi-file Example**:
If you have `main.c`, `helper.c`, and `math.c` in the same folder:
```python
# Point to the entry file. The builder finds the rest.
builder.wrapper.build_with_wrapper(source="source/main.c", ...)
```

**Link Time Optimization (LTO)**:
To enable cross-module inlining (e.g., inlining `helper.c` functions into `main.c`), enable LTO in `config/toolchain.yaml`:
```yaml
compiler:
  flags: ["-flto"]
linker:
  flags: ["-flto"]
```
This produces a single, highly optimized instruction stream, eliminating function call overhead.

---

### 5.5 Symbol Bridge (Calling Firmware Functions)

The **Symbol Bridge** allows your JIT code to call functions that exist in the main firmware (e.g., `printf`, `esp_timer_get_time`, `heap_caps_malloc`) without re-implementing them.

**Prerequisites**:
1.  **Configure Firmware ELF**: Set the path to your firmware's ELF file in `config/toolchain.yaml`:
    ```yaml
    linker:
      firmware_elf: "/path/to/p4_jit_firmware.elf"
    ```
2.  **Enable in Build**: Pass `use_firmware_elf=True` to the builder.

**Example**:
```c
// hello.c
#include <stdio.h> // Standard header provides signature

void say_hello() {
    // Calls the firmware's printf at runtime!
    printf("Hello from JIT!\n"); 
}
```

```python
# Build with Symbol Bridge enabled
builder.wrapper.build_with_wrapper(
    source="hello.c", 
    function_name="say_hello",
    base_address=code_addr, 
    arg_address=args_addr,
    use_firmware_elf=True  # <--- Magic Flag
)
```

**How it works**:
The linker reads the symbol table from the firmware ELF and resolves function calls to their absolute addresses in the device's memory (e.g., `printf` -> `0x400167a6`). This adds **zero overhead** to your JIT binary.

---

## 6. API Reference

### `esp32_loader.builder.Builder`
*   `__init__(config_path)`: Load toolchain config.
*   `build(source, output, ...)`: Low-level compile.
*   `wrapper.build_with_wrapper(source, function_name, base_address, arg_address)`: High-level build with ABI wrapper.

### `esp32_loader.binary_object.BinaryObject`
Represents the compiled binary artifact.

**Properties**
*   `binary.data`: Raw binary data (bytes).
*   `binary.total_size`: Total size including BSS padding.
*   `binary.base_address`: The linked load address.
*   `binary.entry_address`: Address of the entry point.
*   `binary.functions`: List of all functions and their addresses.

**Methods**
*   `save_bin(path)`: Save raw binary file.
*   `save_elf(path)`: Save ELF file with debug symbols.
*   `save_metadata(path)`: Save JSON metadata.
*   `print_sections()`: Print section table.
*   `print_symbols()`: Print symbol table.
*   `print_memory_map()`: Print visual memory map.
*   `disassemble(output)`: Disassemble code to file or stdout.
*   `get_data()`: Get raw bytes.
*   `get_metadata_dict()`: Get metadata as dictionary.
*   `get_function_address(name)`: Get address of a specific function.
*   `validate()`: Perform internal validation checks.

### `p4_jit.jit_session.JITSession`
*   `connect(port=None)`: Connect to device.
*   `load_function(binary_object, args_addr)`: Upload binary and return `RemoteFunction` handle.

### `p4_jit.device_manager.DeviceManager`
*   `allocate(size, caps, alignment)`: Request memory.
*   `free(address)`: Release memory.
*   `write_memory(address, data)`: Write binary data.
*   `read_memory(address, size)`: Read binary data.
*   `execute(address)`: Transfer control to address.

---

## 7. Communication Protocol Specification

The protocol is a request-response binary protocol over USB CDC-ACM.

**Endianness**: Little-Endian
**Packet Format**:
```
| Offset | Field    | Size | Description |
|:-------|:---------|:-----|:------------|
| 0      | Magic    | 2    | 0xA5 0x5A   |
| 2      | Cmd ID   | 1    | Command ID  |
| 3      | Flags    | 1    | 0x00=Req, 0x01=OK, 0x02=Err |
| 4      | Length   | 4    | Payload Length (N) |
| 8      | Payload  | N    | Data |
| 8+N    | Checksum | 2    | Sum(Header + Payload) |
```

**Commands**:
*   **PING (0x01)**: Echo payload.
*   **ALLOC (0x10)**:
    *   Req: `Size(4) | Caps(4) | Align(4)`
    *   Resp: `Addr(4) | Error(4)`
*   **FREE (0x11)**:
    *   Req: `Addr(4)`
    *   Resp: `Status(4)`
*   **WRITE (0x20)**:
    *   Req: `Addr(4) | Data(N)`
    *   Resp: `Written(4) | Status(4)`
*   **READ (0x21)**:
    *   Req: `Addr(4) | Size(4)`
    *   Resp: `Data(N)`
*   **EXEC (0x30)**:
    *   Req: `Addr(4)`
    *   Resp: `RetVal(4)`

---

## 8. Internals & Design Decisions

### 8.1 Why Position Specific Code?
We avoided Position Independent Code (PIC) because:
1.  **Performance**: PIC requires indirect addressing via a Global Offset Table (GOT), which adds instruction overhead.
2.  **Complexity**: Implementing a dynamic linker on the ESP32 to resolve GOT entries at runtime is complex and error-prone.
3.  **Simplicity**: By linking for a specific address, we get standard, optimized machine code that just works, provided we load it at the right place.

### 8.2 Automatic ABI Wrapping
The ESP32-P4 uses the RISC-V ILP32F ABI (arguments in registers `a0`-`a7`, `fa0`-`fa7`). Python cannot easily set CPU registers remotely.
**Solution**: We use a "Shared Memory" approach.
1.  Host writes args to a memory buffer.
2.  We generate a C wrapper that:
    *   Reads from the buffer.
    *   Casts data to the correct types (handling float bit-patterns).
    *   Calls the target function (compiler handles register allocation).
    *   Writes the result back to the buffer.

### 8.3 Cache Coherency & Safety
The ESP32-P4 has separate Instruction (I) and Data (D) caches.
*   When we `WRITE` code, it goes through the D-Cache to RAM.
*   The I-Cache might still contain stale data for that address.
*   **Critical Step**: The firmware calls `esp_cache_msync()` with `ESP_CACHE_MSYNC_FLAG_INVALIDATE`. This forces the D-Cache to flush to RAM and invalidates the I-Cache, ensuring the CPU fetches the new instructions.

---

## 9. Troubleshooting

| Error | Likely Cause | Solution |
|:------|:-------------|:---------|
| `Device not connected` | USB issue or Port busy | Check cable, close other terminals (Putty/TeraTerm). |
| `PermissionError` | Host-side safety check | You are writing to an address you didn't `allocate()`. |
| `IllegalInstruction` | Cache incoherency | Ensure `esp_cache_msync` is working. Check `-march` in config. |
| `LoadProhibited` | Null pointer dereference | Check your C code. |
| `Linker Error` | Code size > Allocation | Increase allocation size (add padding). |

---
