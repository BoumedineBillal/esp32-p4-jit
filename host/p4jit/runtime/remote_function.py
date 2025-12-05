import struct
from typing import Any, Optional, Dict
from .smart_args import SmartArgs
from ..utils.logger import setup_logger, INFO_VERBOSE

logger = setup_logger(__name__)

class RemoteFunction:
    """
    Represents a function loaded on the remote device.
    """
    def __init__(self, device_manager, code_addr: int, args_addr: int, 
                 signature: Optional[Dict[str, Any]] = None, smart_args: bool = False,
                 sync_arrays: bool = True):
        self.dm = device_manager
        self.code_addr = code_addr
        self.args_addr = args_addr
        self.signature = signature
        self.smart_args = smart_args
        
        # PERSISTENT CONFIGURATION
        self.sync_enabled = sync_arrays

    def __call__(self, *args) -> Any:
        """
        Call the remote function.
        """
        logger.debug(f"Calling remote function at 0x{self.code_addr:08X}")
        
        if self.smart_args:
            if not self.signature:
                logger.error("Smart args enabled but no signature provided")
                raise ValueError("Smart args enabled but no signature provided")
            
            # FRESH HANDLER PER CALL
            # Pass the persistent configuration 'self.sync_enabled'
            handler = SmartArgs(self.dm, self.signature, sync_enabled=self.sync_enabled)
            
            try:
                # Pack arguments using SmartArgs
                logger.log(INFO_VERBOSE, "Packing arguments...")
                args_blob = handler.pack(*args)
                
                # Write Arguments
                self.dm.write_memory(self.args_addr, args_blob)
                
                # Execute
                self.dm.execute(self.code_addr)
                
                # Sync Back using the fresh handler
                handler.sync_back()
                
                # Read and convert return value
                return handler.get_return_value(self.args_addr)
                
            finally:
                # Cleanup allocated memory
                handler.cleanup()
                
        else:
            # Legacy mode: Expect single bytes argument
            if len(args) != 1 or not isinstance(args[0], bytes):
                raise ValueError("In legacy mode (smart_args=False), expected single bytes argument")
            
            args_blob = args[0]
            
            # 1. Write Arguments
            self.dm.write_memory(self.args_addr, args_blob)
            
            # 2. Execute
            result = self.dm.execute(self.code_addr)
            
            return result
