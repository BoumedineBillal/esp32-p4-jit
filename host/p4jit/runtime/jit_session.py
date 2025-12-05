import serial.tools.list_ports
from .device_manager import DeviceManager
from .remote_function import RemoteFunction
from ..utils.logger import setup_logger, INFO_VERBOSE

logger = setup_logger(__name__)

class JITSession:
    """
    Orchestrates the JIT session, handling device discovery and function loading.
    """
    def __init__(self):
        self.device = DeviceManager()

    def connect(self, port: str = None):
        """
        Connect to the device. If port is not specified, attempts to auto-detect
        by sending PING to available ports.
        """
        if port:
            self.device.port = port
            logger.info(f"Connecting to specified port: {port}")
            self.device.connect()
            if not self.device.ping():
                self.device.disconnect()
                logger.error(f"Device at {port} did not respond to PING")
                raise RuntimeError(f"Device at {port} did not respond to PING")
        else:
            logger.info("Auto-detecting JIT device...")
            found = False
            ports = list(serial.tools.list_ports.comports())
            
            if not ports:
                logger.warning("No serial ports found on the system.")
            
            for p in ports:
                try:
                    logger.debug(f"Probing {p.device}...")
                    self.device.port = p.device
                    self.device.connect()
                    if self.device.ping():
                        found = True
                        logger.info(f"Found JIT Device at {p.device}")
                        break
                    self.device.disconnect()
                except Exception as e:
                    logger.debug(f"Probe failed for {p.device}: {e}")
                    pass
            
            if not found:
                logger.critical("Could not find JIT Device on any port")
                raise RuntimeError("Could not find JIT Device on any port")

    def load_function(self, binary_object, args_addr: int, smart_args: bool = False) -> RemoteFunction:
        """
        Load a function onto the device and return a callable wrapper.
        
        Args:
            binary_object: The compiled BinaryObject.
            args_addr: The address of the arguments buffer on the device.
            smart_args: If True, enables automatic argument processing (NumPy support).
            
        Returns:
            RemoteFunction: A callable object to execute the function.
        """
        # 1. Upload Code
        logger.log(INFO_VERBOSE, f"Uploading code to 0x{binary_object.base_address:08X} ({len(binary_object.data)} bytes)")
        self.device.write_memory(binary_object.base_address, binary_object.data)
        
        # 2. Return Wrapper
        # Pass metadata (signature) if available, required for smart_args
        signature = None
        if smart_args:
            if not hasattr(binary_object, 'metadata') or not binary_object.metadata:
                # Try to load from file if not in object
                # This is a fallback, ideally metadata is attached during build
                logger.warning("SmartArgs requested but binary metadata missing.")
                pass
            else:
                # Extract signature from metadata
                # Metadata structure: {'functions': [{'name': '...', ...}], ...}
                # We need the full signature which is usually in signature.json
                # BinaryObject.metadata currently stores what MetadataGenerator produces
                # which includes 'parameters' and 'return_type' at the top level for the single wrapped function
                signature = binary_object.metadata
                logger.debug(f"Loaded signature for SmartArgs: {signature.get('name', 'unknown')}")
        
        return RemoteFunction(self.device, binary_object.entry_address, args_addr, 
                              signature=signature, smart_args=smart_args)
