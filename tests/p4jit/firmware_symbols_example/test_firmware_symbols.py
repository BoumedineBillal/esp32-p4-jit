import os
import sys
import time

# Add host directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'host')))

import p4jit

# Configure logging to verify detailed output
p4jit.set_log_level('INFO_VERBOSE')

def main():
    print("==============================================")
    print("      Test: Firmware Symbols (printf/malloc)  ")
    print("==============================================")
    
    # Initialize JIT
    try:
        jit = p4jit.P4JIT()
    except Exception as e:
        print(f"Failed to initialize P4JIT: {e}")
        return

    # Define source file path
    source_file = os.path.join(os.path.dirname(__file__), 'source', 'dynamic_print.c')
    
    # 1. Load Function
    # We explicitly set use_firmware_elf=True to ensure symbols are resolved
    try:
        func = jit.load(
            source=source_file,
            function_name="test_dynamic",
            use_firmware_elf=True
        )
    except FileNotFoundError as e:
        print("\n[ERROR] Build Failed:")
        print(f"  {e}")
        print("\nHint: Check config/toolchain.yaml 'firmware_elf' path.")
        return
    except Exception as e:
        print(f"\n[ERROR] Unexpected error during load: {e}")
        return

    # 2. Execute Function
    print("\n[Test] Executing 'test_dynamic' on device...")
    print("----------------------------------------------")
    
    # Expect output in device logs (monitor)
    # The function returns an integer (42)
    start_time = time.time()
    try:
        result = func()
        duration = time.time() - start_time
        print("----------------------------------------------")
        print(f"[Test] Execution complete in {duration:.3f}s")
        print(f"[Test] Return Value: {result}")
        
        if result == 42:
            print("\n[SUCCESS] Test Passed!")
        else:
            print(f"\n[FAILURE] Unexpected return value: {result} (Expected: 42)")
            
    except Exception as e:
        print(f"\n[FAILURE] Execution error: {e}")

    # Cleanup
    func.free()
    jit.session.device.disconnect()

if __name__ == "__main__":
    main()
