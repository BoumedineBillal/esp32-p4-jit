import os
import sys
import time

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from esp32_loader import Builder
from p4_jit import JITSession
from p4_jit.memory_caps import MALLOC_CAP_SPIRAM, MALLOC_CAP_8BIT, MALLOC_CAP_INTERNAL


print("Testing Printf with Symbol Bridge...")

# 1. Setup Paths
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
firmware_elf = os.path.join(project_root, 'p4_jit_firmware', 'build', 'p4_jit_firmware.elf')

if not os.path.exists(firmware_elf):
    print(f"Error: Firmware ELF not found at {firmware_elf}")
    print("Please build the firmware first.")
    sys.exit()

# 2. Initialize Builder
# Firmware ELF path is now read from config/toolchain.yaml
builder = Builder()

# 3. Connect to Device
session = JITSession()
try:
    session.connect()
except Exception as e:
    print(f"Failed to connect: {e}")
    sys.exit()

# 4. Build (Pass 1 - Probe)
print("Building (Pass 1)...")
source_file = os.path.join(os.path.dirname(__file__), 'source', 'hello.c')
try:
    temp_bin = builder.wrapper.build_with_wrapper(
        source=source_file, 
        function_name="hello_world",
        base_address=0, 
        arg_address=0,
        use_firmware_elf=True
    )
except RuntimeError as e:
    print(f"Build failed: {e}")
    sys.exit()

# 5. Allocate Memory
# Use L2MEM (Internal) for code if possible, or SPIRAM
CAP_EXEC = MALLOC_CAP_INTERNAL 
CAP_DATA = MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT

print(f"Allocating {temp_bin.total_size} bytes for code...")
code_addr = session.device.allocate(temp_bin.total_size + 64, CAP_EXEC, 128)
args_addr = session.device.allocate(128, CAP_DATA, 128)
print(f"Code allocated at: 0x{code_addr:08x}")

# 6. Build (Pass 2 - Final)
print("Building (Pass 2)...")
final_bin = builder.wrapper.build_with_wrapper(
    source=source_file, 
    function_name="hello_world",
    base_address=code_addr, 
    arg_address=args_addr,
    use_firmware_elf=True
)

# 7. Load & Execute
print("Loading function...")
remote_func = session.load_function(final_bin, args_addr)

print("Executing...")
# No arguments needed for this function
remote_func(b'')

print("Execution complete! Check the device monitor for 'Hello from JIT!' output.")
session.device.disconnect()

final_bin.disassemble("asm.txt", False)
final_bin.print_memory_map()
final_bin.print_sections()



