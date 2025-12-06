# P4-JIT Component

A high-performance dynamic code loading system for ESP32-P4 microcontrollers that enables execution of native RISC-V machine code compiled on-the-fly from a host PC.

---

## Overview

The P4-JIT component provides a USB-based protocol for dynamic code loading and execution on the ESP32-P4. Unlike interpreted languages or bytecode VMs, this system executes **native, optimized RISC-V machine code**, delivering maximum performance for computationally intensive tasks.

### Key Features

- **Native Code Execution**: Direct RISC-V instruction execution with zero interpreter overhead
- **USB High-Speed Transport**: Efficient binary protocol over TinyUSB CDC-ACM (~10-12 MB/s)
- **Dynamic Memory Management**: Runtime allocation with ESP-IDF heap capabilities (PSRAM/SRAM, executable/data)
- **Cache Coherency**: Automatic instruction/data cache synchronization via `esp_cache_msync()`
- **FreeRTOS Integration**: Non-blocking operation via dedicated task and stream buffers
- **Memory Safety**: Shadow allocation table prevents segmentation faults
- **Configurable**: Full control over task priority, core affinity, and buffer sizes via Kconfig

### Use Cases

- **Digital Signal Processing (DSP)**: Real-time audio/video processing algorithms
- **Machine Learning Inference**: Optimized neural network kernels
- **Real-Time Control**: Low-latency control loops without firmware reflashing
- **Cryptographic Operations**: Custom encryption/decryption routines
- **Rapid Prototyping**: Algorithm development with 1-2 second iteration cycles

---

## Architecture

```
Host PC                          ESP32-P4
┌────────────────┐              ┌─────────────────┐
│  Python Client │              │  USB Transport  │
│  (p4_jit)      │◄────USB─────►│  (TinyUSB CDC)  │
└────────────────┘              └────────┬────────┘
                                         │
                                ┌────────▼────────┐
                                │ Protocol Parser │
                                │  (State Machine)│
                                └────────┬────────┘
                                         │
                                ┌────────▼────────┐
                                │ Command Handler │
                                │  (Dispatcher)   │
                                └────────┬────────┘
                                         │
                      ┌──────────────────┼─────────────────┐
                      │                  │                 │
               ┌──────▼──────┐  ┌────────▼────────┐  ┌─────▼─────┐
               │   Memory    │  │  Code Executor  │  │   Cache   │
               │  Manager    │  │  (Function Call)│  │  Manager  │
               └─────────────┘  └─────────────────┘  └───────────┘
```

### Component Structure

```
components/p4_jit/
├── src/
│   ├── p4_jit.c           # Component initialization, task management
│   ├── protocol.c         # Binary protocol parser, packet handling
│   ├── commands.c         # Command dispatcher (ALLOC, WRITE, EXEC, etc.)
│   └── usb_transport.c    # TinyUSB CDC-ACM, StreamBuffer management
├── include/
│   └── p4_jit.h           # Public API header
├── Kconfig                # Component configuration options
├── CMakeLists.txt         # ESP-IDF build integration
└── sdkconfig.defaults.p4_jit  # Default system configuration
```

---

## Dependencies

### Required IDF Components
- `esp_timer` - High-resolution timing
- `driver` - Hardware abstraction layer
- `esp_rom` - ROM functions
- `esp_mm` - Memory management APIs
- `heap` - Heap allocator with capabilities
- `log` - Logging system

### External Dependencies
- `espressif/esp_tinyusb` (v2.0.1+) - USB stack

### System Requirements
- **ESP-IDF**: v5.0 or later (tested with v5.4.0, v5.5.0)
- **Hardware**: ESP32-P4 with PSRAM (16MB+ recommended)
- **Toolchain**: riscv32-esp-elf-gcc (esp-14.2.0+ recommended)

---

## Installation

### Step 1: Add Component to Your Project

Copy the `p4_jit` component to your project's components directory:

```bash
cp -r /path/to/p4_jit components/
```

Or add as a Git submodule:

```bash
cd components
git submodule add <repository_url> p4_jit
```

### Step 2: Install Component Dependencies

Use the IDF Component Manager to install TinyUSB:

```bash
idf.py add-dependency "espressif/esp_tinyusb^2.0.1"
idf.py reconfigure
```

Or add to your `main/idf_component.yml`:

```yaml
dependencies:
  espressif/esp_tinyusb: "^2.0.1"
```

### Step 3: Configure System Requirements

Append the provided defaults to your project's `sdkconfig.defaults.esp32p4`:

```bash
cat components/p4_jit/sdkconfig.defaults.p4_jit >> sdkconfig.defaults.esp32p4
```

**Critical settings** (automatically included via defaults file):

```kconfig
# Memory Protection - CRITICAL FOR JIT EXECUTION
CONFIG_ESP_SYSTEM_PMP_IDRAM_SPLIT=n
CONFIG_SOC_SPIRAM_XIP_SUPPORTED=y

# External PSRAM
CONFIG_SPIRAM=y
CONFIG_SPIRAM_SPEED_200M=y

# Cache Configuration
CONFIG_CACHE_L2_CACHE_256KB=y
CONFIG_CACHE_L2_CACHE_LINE_128B=y

# Watchdogs (Disable for debugging)
CONFIG_ESP_INT_WDT=n
CONFIG_ESP_TASK_WDT_EN=n

# USB Communication
CONFIG_TINYUSB_CDC_ENABLED=y
CONFIG_TINYUSB_CDC_COUNT=1
CONFIG_TINYUSB_CDC_RX_BUFSIZE=2048
CONFIG_TINYUSB_CDC_TX_BUFSIZE=2048
```

**⚠️ CRITICAL**: `CONFIG_ESP_SYSTEM_PMP_IDRAM_SPLIT=n` is **mandatory**. Without this, code execution from data memory will fail with `IllegalInstruction` errors.

### Step 4: Build and Flash

```bash
idf.py set-target esp32p4
idf.py build
idf.py flash monitor
```

---

## Configuration Options

Configure via `idf.py menuconfig` → **Component config** → **P4-JIT Configuration**:

| Option | Default | Range | Description |
|:-------|:--------|:------|:------------|
| `P4_JIT_TASK_STACK_SIZE` | 8192 | 4096-32768 | Stack size for protocol task (bytes) |
| `P4_JIT_TASK_PRIORITY` | 5 | 0-25 | FreeRTOS task priority |
| `P4_JIT_TASK_CORE_ID` | 1 | -1, 0, 1 | CPU core assignment (-1=no affinity) |
| `P4_JIT_PAYLOAD_BUFFER_SIZE` | 1048576 | 64K-4M | RX/TX buffer for code transfer (bytes) |
| `P4_JIT_STREAM_BUFFER_SIZE` | 16384 | 4K-64K | USB ISR ring buffer (bytes) |

### Recommended Settings

**Development/Debugging:**
```kconfig
CONFIG_P4_JIT_TASK_PRIORITY=5
CONFIG_P4_JIT_TASK_CORE_ID=1
CONFIG_P4_JIT_PAYLOAD_BUFFER_SIZE=1048576  # 1MB
CONFIG_P4_JIT_STREAM_BUFFER_SIZE=16384     # 16KB
```

**Production/High Performance:**
```kconfig
CONFIG_P4_JIT_TASK_PRIORITY=10  # Higher priority if JIT is critical path
CONFIG_P4_JIT_TASK_CORE_ID=1    # Dedicated core for deterministic latency
CONFIG_P4_JIT_STREAM_BUFFER_SIZE=32768  # 32KB to reduce packet loss under load
```

---

## API Reference

### Initialization

```c
#include "p4_jit.h"

void app_main(void) {
    // Start with default configuration
    ESP_ERROR_CHECK(p4_jit_start(NULL));
    
    // Your application continues running...
    while (1) {
        // Main application logic
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

### Custom Configuration

```c
p4_jit_config_t config = {
    .task_priority = 10,           // Higher priority
    .task_core_id = 1,             // Pin to Core 1
    .stack_size = 16384,           // 16KB stack
    .rx_buffer_size = 0,           // Reserved for future use
    .tx_buffer_size = 0            // Reserved for future use
};

ESP_ERROR_CHECK(p4_jit_start(&config));
```

### Function: `p4_jit_start()`

```c
esp_err_t p4_jit_start(const p4_jit_config_t *config);
```

**Description**: Initialize and start the P4-JIT engine in a background task.

**Parameters**:
- `config`: Pointer to configuration struct (pass `NULL` for defaults from Kconfig)

**Returns**:
- `ESP_OK`: Success
- `ESP_ERR_INVALID_STATE`: Engine already running
- `ESP_FAIL`: Task creation failed

**Notes**:
- Non-blocking - returns immediately after spawning task
- USB transport is initialized automatically
- Protocol loop runs in dedicated FreeRTOS task

### Function: `p4_jit_stop()`

```c
esp_err_t p4_jit_stop(void);
```

**Description**: Stop the JIT engine and free resources.

**Returns**:
- `ESP_OK`: Success

**Notes**:
- Currently experimental - protocol loop is infinite
- Deletes the JIT task but does not cleanup all resources

---

## Communication Protocol

### Packet Format

All communication uses a binary protocol with the following structure:

```
┌────────┬─────────┬───────┬────────┬──────────┬──────────┐
│ Magic  │ Command │ Flags │ Length │ Payload  │ Checksum │
│ 2 bytes│ 1 byte  │ 1 byte│ 4 bytes│ N bytes  │ 2 bytes  │
└────────┴─────────┴───────┴────────┴──────────┴──────────┘
```

| Offset | Field | Size | Description |
|:-------|:------|:-----|:------------|
| 0 | Magic | 2 | Sync bytes: `0xA5 0x5A` |
| 2 | Command | 1 | Command ID (see table below) |
| 3 | Flags | 1 | `0x00`=Request, `0x01`=OK, `0x02`=Error |
| 4 | Length | 4 | Payload length (little-endian) |
| 8 | Payload | N | Command-specific data |
| 8+N | Checksum | 2 | Sum(Header + Payload) & 0xFFFF |

### Supported Commands

| Command ID | Name | Description | Request Payload | Response Payload |
|:-----------|:-----|:------------|:----------------|:-----------------|
| `0x01` | PING | Echo test | Arbitrary bytes | Same bytes echoed back |
| `0x10` | ALLOC | Allocate memory | `size(4), caps(4), align(4)` | `address(4), error(4)` |
| `0x11` | FREE | Release memory | `address(4)` | `status(4)` |
| `0x20` | WRITE_MEM | Write data | `address(4), data(N)` | `bytes_written(4), status(4)` |
| `0x21` | READ_MEM | Read data | `address(4), size(4)` | `data(N)` |
| `0x30` | EXEC | Execute code | `address(4)` | `return_value(4)` |
| `0x40` | HEAP_INFO | Get heap stats | Empty | `free_spiram(4), total_spiram(4), free_internal(4), total_internal(4)` |

### Error Codes

| Code | Name | Description |
|:-----|:-----|:------------|
| `0x00` | ERR_OK | Success |
| `0x01` | ERR_CHECKSUM | Checksum mismatch |
| `0x02` | ERR_UNKNOWN_CMD | Unknown command ID |
| `0x03` | ERR_ALLOC_FAIL | Memory allocation failed |

### Memory Capabilities

Memory allocation uses ESP-IDF heap capability flags:

```c
// Common combinations
MALLOC_CAP_SPIRAM                  // External PSRAM
MALLOC_CAP_INTERNAL                // Internal SRAM
MALLOC_CAP_8BIT                    // Byte-accessible
MALLOC_CAP_EXEC | MALLOC_CAP_8BIT  // Executable code region
MALLOC_CAP_DMA                     // DMA-capable
```

**Example - Allocate executable PSRAM**:
```python
# Host-side (Python)
caps = MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT
address = device.allocate(size=4096, caps=caps, alignment=16)
```

---

## Integration Example

### Minimal Application

```c
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "p4_jit.h"

static const char *TAG = "main";

void app_main(void)
{
    ESP_LOGI(TAG, "Starting Application with P4-JIT");

    // Initialize JIT engine (runs in background)
    ESP_ERROR_CHECK(p4_jit_start(NULL));

    ESP_LOGI(TAG, "JIT Engine ready. Connect via USB.");

    // Main application loop
    while (1) {
        // Your application logic here
        ESP_LOGI(TAG, "Main app running...");
        vTaskDelay(pdMS_TO_TICKS(5000));
    }
}
```

### Build and Flash

```bash
idf.py set-target esp32p4
idf.py build
idf.py flash monitor
```

**Expected output**:
```
I (XXX) main: Starting Application with P4-JIT
I (XXX) p4_jit: Initializing USB Transport...
I (XXX) p4_jit: Stream buffer created
I (XXX) p4_jit: TinyUSB driver installed
I (XXX) p4_jit: USB Initialized
I (XXX) p4_jit: Starting JIT Task (Prio:5, Core:1, Stack:8192)
I (XXX) main: JIT Engine ready. Connect via USB.
I (XXX) p4_jit: JIT Task started on Core 1
I (XXX) protocol: Protocol loop started
I (XXX) main: Main app running...
```

---

## Troubleshooting

### Issue: `Guru Meditation Error: IllegalInstruction`

**Symptoms**: Device crashes immediately when executing JIT code.

**Cause**: Physical Memory Protection (PMP) blocking code execution from data regions.

**Solution**:
1. Verify `CONFIG_ESP_SYSTEM_PMP_IDRAM_SPLIT=n` in `sdkconfig`
2. Rebuild completely:
   ```bash
   idf.py fullclean
   idf.py build
   idf.py flash
   ```

**Verification**:
```bash
grep "CONFIG_ESP_SYSTEM_PMP_IDRAM_SPLIT" sdkconfig
# Should show: CONFIG_ESP_SYSTEM_PMP_IDRAM_SPLIT=n
```

---

### Issue: USB Device Not Enumerated

**Symptoms**: Host PC doesn't detect ESP32-P4 as USB serial device.

**Cause**: TinyUSB not configured or conflicting USB console.

**Solution**:
1. Verify TinyUSB is enabled:
   ```bash
   grep "CONFIG_TINYUSB_CDC_ENABLED" sdkconfig
   # Should show: CONFIG_TINYUSB_CDC_ENABLED=y
   ```

2. Disable USB console (it conflicts with JIT):
   ```bash
   idf.py menuconfig
   # Navigate to: Component config → ESP System Settings
   # Set "Channel for console output" to UART
   ```

3. Rebuild and flash

**Verification**:
```bash
# Linux/macOS
ls /dev/ttyACM*

# Windows
# Check Device Manager → Ports (COM & LPT)
```

---

### Issue: Cache Sync Errors

**Symptoms**: Logs show `Cache sync failed: 0x...` errors.

**Cause**: Misaligned addresses for `esp_cache_msync()` (must be 128-byte aligned).

**Solution**: The component automatically aligns addresses. If errors persist:

1. Increase allocation alignment on host side:
   ```python
   # Instead of alignment=4
   address = device.allocate(size, caps, alignment=128)
   ```

2. Verify cache line size configuration:
   ```bash
   grep "CONFIG_CACHE_L2_CACHE_LINE" sdkconfig
   # Should show: CONFIG_CACHE_L2_CACHE_LINE_128B=y
   ```

---

### Issue: Task Watchdog Triggered

**Symptoms**: `Task watchdog got triggered. The following tasks did not reset the watchdog in time: jit_task`

**Cause**: JIT task blocked during long memory transfers or compilation.

**Solution**:
1. **For Development**: Disable watchdogs completely:
   ```kconfig
   CONFIG_ESP_INT_WDT=n
   CONFIG_ESP_TASK_WDT_EN=n
   ```

2. **For Production**: Increase watchdog timeout:
   ```bash
   idf.py menuconfig
   # Component config → Common ESP-related → Task Watchdog timeout period
   # Increase to 10+ seconds
   ```

---

### Issue: Memory Allocation Failures

**Symptoms**: `CMD_ALLOC: Failed` or `Allocation failed on device. Error: 3`

**Cause**: Insufficient PSRAM or memory fragmentation.

**Solution**:
1. Check available heap:
   ```python
   stats = jit.get_heap_stats()
   print(f"Free SPIRAM: {stats['free_spiram']/1024:.2f} KB")
   ```

2. Verify PSRAM is enabled:
   ```bash
   grep "CONFIG_SPIRAM" sdkconfig
   # Should show: CONFIG_SPIRAM=y
   ```

3. Increase payload buffer size if needed:
   ```bash
   idf.py menuconfig
   # P4-JIT Configuration → JIT Payload Buffer Size
   # Increase from 1MB to 2MB
   ```

4. Free previously allocated memory:
   ```python
   func.free()  # Release function resources
   ```

---

### Issue: Protocol Timeout/Hangs

**Symptoms**: Host-side operations timeout waiting for device response.

**Cause**: USB stream buffer overflow or communication desynchronization.

**Solution**:
1. Increase stream buffer size:
   ```bash
   idf.py menuconfig
   # P4-JIT Configuration → USB Stream Buffer Size
   # Increase from 16KB to 32KB or 64KB
   ```

2. Reduce payload size for large transfers (split into chunks on host side)

3. Reset device and reconnect:
   ```bash
   idf.py flash monitor
   ```

---

## Performance Characteristics

### Throughput
- **USB Transfer Rate**: 10-12 MB/s (High-Speed mode, actual speed depends on USB host controller)
- **Code Upload Time**: ~100ms for 1MB binary (typical DSP algorithm)
- **Execution Latency**: <10µs (function call overhead from protocol to execution)

### Memory Requirements
- **Component ROM**: ~15KB (code in flash)
- **Component RAM**: ~8KB (task stack + protocol buffers)
- **Component PSRAM**: Configurable (default 1MB for payload buffers)
- **Per-Function Overhead**: 0 bytes runtime overhead (direct function pointer calls)

### Timing Comparison

| Operation | Firmware Reflash | P4-JIT |
|:----------|:-----------------|:-------|
| Edit code | 1s | 1s |
| Compile | 5-10s | 1-2s |
| Upload | 10-20s | 0.1s |
| Reboot | 2-5s | 0s |
| **Total** | **18-36s** | **2-3s** |

**Speedup**: 6-12x faster iteration cycles

---

## Advanced Usage

### Multi-Core Execution

Pin JIT task to dedicated core for deterministic performance:

```c
p4_jit_config_t config = {
    .task_core_id = 1,  // Isolate on Core 1
    .task_priority = 15 // High priority
};
p4_jit_start(&config);
```

**Benefits**:
- Prevents cache thrashing from Wi-Fi/system tasks on Core 0
- Reduces jitter in real-time applications
- Improves throughput for compute-intensive workloads

### Firmware Symbol Resolution

JIT code can call firmware functions (malloc, printf, FreeRTOS APIs) by enabling symbol resolution on the host side during linking.

**Host-side configuration**:
```python
# In config/toolchain.yaml
linker:
  firmware_elf: "firmware/build/your_firmware.elf"
```

**Example - Calling printf from JIT code**:
```c
// JIT code (compiled on host, executed on device)
#include <stdio.h>

int test_function(void) {
    printf("Hello from JIT!\n");  // Resolved to firmware's printf
    return 42;
}
```

**Monitor output**:
```
I (XXX) protocol: Executing at 0x3C000004
Hello from JIT!
I (XXX) protocol: Returned: 42
```

---

## Known Limitations

### L2MEM Execution Constraint

**Issue**: Code allocated in L2MEM (internal SRAM, `0x4FF00000` range) may fail execution despite `CONFIG_ESP_SYSTEM_PMP_IDRAM_SPLIT=n`.

**Reason**: ESP-IDF v5.4+ enforces stricter PMP rules that mark L2MEM as non-executable by default.

**Workaround**: Allocate code in PSRAM instead:
```python
# Use PSRAM for code allocation
caps = MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT
code_addr = device.allocate(size, caps, alignment=16)
```

**Performance Impact**: Minimal when using L2 cache (256KB configuration recommended).

### Type System Constraints

See main project documentation (`docs/LIMITATIONS.md`) for complete type system limitations:
- 4-byte slot size limits `int64_t` and `double`
- Struct return values require hidden pointer workaround
- All arguments must fit in 32-slot args array (31 usable, 1 reserved for return)

---

## Security Considerations

### Memory Safety

The component implements basic memory safety:
- **Shadow Allocation Table**: Tracks all allocations to prevent wild pointer access
- **Bounds Checking**: Validates read/write operations against allocated regions
- **Checksum Validation**: Detects corrupted packets

**However**:
- ⚠️ No authentication - any USB client can execute arbitrary code
- ⚠️ No sandboxing - JIT code runs with full firmware privileges
- ⚠️ No resource limits - malicious code can exhaust memory/CPU

**Recommendations for Production**:
1. Disable in production builds (`#ifdef ENABLE_JIT`)
2. Add authentication layer (token-based or certificate)
3. Implement resource quotas (max allocations, execution time limits)
4. Use separate firmware partition for JIT (isolation)

---

## Version History

### v1.0.0 (Current)
- Initial release
- USB High-Speed transport (TinyUSB CDC-ACM)
- Dynamic memory allocation with heap capabilities
- Automatic cache coherency management (`esp_cache_msync`)
- FreeRTOS task integration with configurable priority/core
- Binary protocol with checksum validation
- Support for PING, ALLOC, FREE, WRITE_MEM, READ_MEM, EXEC, HEAP_INFO commands
- Shadow allocation table for memory safety
- Tested on ESP-IDF v5.4.0, v5.5.0

---

## License

MIT License - See project root for full license text.

---

## Support

### Getting Help

1. **Check Documentation**:
   - Main project README: `/README.md`
   - Technical Reference: `/docs/TRM.md`
   - Limitations Guide: `/docs/LIMITATIONS.md`

2. **Verify Configuration**:
   ```bash
   grep "CONFIG_ESP_SYSTEM_PMP_IDRAM_SPLIT" sdkconfig
   grep "CONFIG_SPIRAM" sdkconfig
   grep "CONFIG_TINYUSB_CDC_ENABLED" sdkconfig
   ```

3. **Enable Verbose Logging**:
   ```bash
   idf.py menuconfig
   # Component config → Log output → Default log verbosity → Verbose
   ```

4. **Collect Debug Information**:
   - Full build log (`idf.py build > build.log 2>&1`)
   - Monitor output (`idf.py monitor > monitor.log`)
   - Host-side logs (enable DEBUG level in Python)

### Reporting Issues

When reporting issues, include:
- ESP-IDF version (`idf.py --version`)
- Hardware details (ESP32-P4 variant, PSRAM size)
- Relevant sdkconfig settings
- Full error logs (both device and host side)
- Minimal reproducible example

---

## Contributing

Contributions to improve the P4-JIT component are welcome!

**Areas for Contribution**:
- Additional protocol commands (e.g., bulk erase, memory dump)
- Enhanced security (authentication, sandboxing)
- Performance optimizations (zero-copy transfers, DMA)
- Additional transport layers (Ethernet, Wi-Fi)
- Improved error handling and recovery

**Development Setup**:
```bash
git clone <repository>
cd esp32-p4-jit
idf.py set-target esp32p4
idf.py menuconfig  # Configure as needed
idf.py build
```

---

**Component Maintained By**: P4-JIT Project  
**Last Updated**: December 2025  
**Compatibility**: ESP-IDF v5.0+, ESP32-P4 only