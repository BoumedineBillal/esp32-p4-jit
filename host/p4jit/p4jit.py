import os
import struct
from typing import Any, Optional, Dict

from .runtime.jit_session import JITSession
from .runtime.device_manager import DeviceManager
from .runtime.memory_caps import MALLOC_CAP_SPIRAM, MALLOC_CAP_8BIT
from .toolchain.builder import Builder
from .toolchain.binary_object import BinaryObject
from .utils.logger import setup_logger, INFO_VERBOSE

logger = setup_logger(__name__)

class JITFunction:
    """
    Represents a specific compiled and loaded function on the device.
    Decouples definition from execution.
    """
    def __init__(self, 
                 session: JITSession, 
                 binary: BinaryObject, 
                 code_addr: int, 
                 args_addr: int, 
                 smart_args: bool):
        self.session = session
        self.binary = binary
        self.code_addr = code_addr
        self.args_addr = args_addr
        self.smart_args = smart_args
        self.valid = True
        
        self.stats = {
            'code_size': binary.total_size,
            'args_size': binary.metadata['addresses']['args_array_bytes'] if binary.metadata else 0,
        }

        # Create Persistent RemoteFunction
        from .runtime.remote_function import RemoteFunction
        
        signature = None
        if self.smart_args and self.binary.metadata:
             signature = self.binary.metadata
             
        self.remote_func = RemoteFunction(
            self.session.device,
            self.code_addr,
            self.args_addr,
            signature=signature,
            smart_args=self.smart_args
        )

    @property
    def sync_arrays(self):
        """Enable/Disable automatic array synchronization."""
        return self.remote_func.sync_enabled

    @sync_arrays.setter
    def sync_arrays(self, value: bool):
        self.remote_func.sync_enabled = value

    def __call__(self, *args) -> Any:
        """
        Execute the function.
        Delegates to the persistent RemoteFunction wrapper.
        """
        if not self.valid:
            logger.error("Attempted to call freed JITFunction")
            raise RuntimeError("JITFunction has been freed and is no longer valid")

        return self.remote_func(*args)

    def free(self):
        """
        Manually release resources.
        """
        if not self.valid:
            return

        try:
            logger.debug(f"Freeing JITFunction resources (Code: 0x{self.code_addr:08x}, Args: 0x{self.args_addr:08x})")
            self.session.device.free(self.code_addr)
            self.session.device.free(self.args_addr)
        except Exception as e:
            logger.warning(f"Failed to free JITFunction resources: {e}")
            
        self.valid = False


class P4JIT:
    """
    The Manager class for P4-JIT operations.
    Aggregates Toolchain and Runtime layers.
    """
    def __init__(self, port: str = None, config_path: str = 'config/toolchain.yaml'):
        """
        Initialize the JIT system.
        """
        logger.info("Initializing P4JIT System...")
        self.session = JITSession()
        self.session.connect(port) # Auto-detect if port is None
        
        # Initialize Builder
        # Builder loads config internally, but we might want to pass config_path if Builder supported it.
        # Current Builder implementation loads from default relative path.
        self.builder = Builder() 
        logger.info("P4JIT Initialized.")

    def get_heap_stats(self, print_s: bool = True) -> Dict[str, int]:
        """
        Get current heap memory statistics from the device.
        
        Args:
            print_s (bool): If True, log stats to INFO. Default is True.
        """
        stats = self.session.device.get_heap_info()
        
        if print_s:
            logger.info("[Heap Params]")
            for k, v in stats.items():
                logger.info(f"  {k:<15}: {v:>10} bytes ({v/1024:>6.2f} KB)")
                
        return stats

    def load(self, 
             source: str, 
             function_name: str,
             # --- Build Configuration ---
             base_address: int = 0x03000004, 
             arg_address: int = 0x00030004,  
             optimization: str = 'O3',       
             output_dir: Optional[str] = None, # Default to None (auto-detect)
             use_firmware_elf: bool = True,  
             # --- Memory Allocation ---
             code_caps: int = MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT, 
             data_caps: int = MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT, 
             alignment: int = 16,            
             # --- Runtime ---
             smart_args: bool = True         
             ) -> JITFunction:
        """
        Builds, allocates, and loads a function.
        """
        
        
        logger.info(f"Loading '{function_name}' from '{os.path.basename(source)}'...")
        
        # 1. Build (Pass 1 - Wrapper Generation & Probe)
        # We need to generate the wrapper first to know the size
        logger.log(INFO_VERBOSE, f"Pass 1: Preliminary Build (Opt: -{optimization})")
        
        # Pass 1: Build with default/requested addresses to get size
        temp_bin = self.builder.wrapper.build_with_wrapper(
            source=source,
            function_name=function_name,
            base_address=base_address,
            arg_address=arg_address,
            output_dir=output_dir,
            use_firmware_elf=use_firmware_elf
        )
        
        # 2. Allocate
        logger.log(INFO_VERBOSE, f"Allocating device memory (Align: {alignment})...")
        
        # Calculate sizes
        # temp_bin.total_size includes text, data, rodata.
        alloc_code_size = temp_bin.total_size + 64 # Safety padding
        
        # Args size comes from metadata
        alloc_args_size = temp_bin.metadata['addresses']['args_array_bytes']
        
        real_code_addr = self.session.device.allocate(alloc_code_size, code_caps, alignment)
        real_args_addr = self.session.device.allocate(alloc_args_size, data_caps, alignment)
        
        logger.info(f"  Code Allocated: 0x{real_code_addr:08X} ({alloc_code_size} bytes)")
        logger.info(f"  Args Allocated: 0x{real_args_addr:08X} ({alloc_args_size} bytes)")
        
        # 3. Link (Pass 2 - Re-build with real addresses)
        logger.log(INFO_VERBOSE, "Pass 2: Re-linking with allocated addresses...")
        final_bin = self.builder.wrapper.build_with_wrapper(
            source=source,
            function_name=function_name,
            base_address=real_code_addr,
            arg_address=real_args_addr,
            output_dir=output_dir,
            use_firmware_elf=use_firmware_elf
        )
        
        # 4. Upload
        logger.log(INFO_VERBOSE, "Uploading binary to device...")
        self.session.device.write_memory(real_code_addr, final_bin.data)
        
        # 5. Instantiate
        logger.info("Function loaded successfully.")
        return JITFunction(
            self.session,
            final_bin,
            real_code_addr,
            real_args_addr,
            smart_args
        )
