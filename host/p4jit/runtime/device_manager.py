import struct
import time
import serial
from typing import Optional, Tuple, Dict
from p4jit.utils.logger import setup_logger, INFO_VERBOSE

logger = setup_logger(__name__)

# Protocol Constants
MAGIC = b'\xA5\x5A'
CMD_PING = 0x01
CMD_ALLOC = 0x10
CMD_FREE = 0x11
CMD_WRITE_MEM = 0x20
CMD_READ_MEM = 0x21
CMD_EXEC = 0x30
CMD_HEAP_INFO = 0x40

ERR_OK = 0x00

class DeviceManager:
    """
    Handles low-level communication with the ESP32-P4 JIT firmware.
    Manages memory allocation tracking and enforces safety.
    """
    def __init__(self, port: str = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        
        # Allocation Table: address -> {size, type, caps, align}
        self.allocations: Dict[int, dict] = {}

    def connect(self):
        if self.port:
            logger.info(f"Connecting to {self.port} at {self.baudrate} baud...")
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1.0)
            logger.info("Connected.")

    def disconnect(self):
        if self.serial and self.serial.is_open:
            self.serial.close()
            logger.info("Disconnected.")

    def _send_packet(self, cmd_id: int, payload: bytes) -> bytes:
        if not self.serial or not self.serial.is_open:
            raise RuntimeError("Device not connected")

        # 1. Construct Header
        # Magic (2), Cmd (1), Flags (1), Len (4)
        header = struct.pack('<2sBB I', MAGIC, cmd_id, 0x00, len(payload))
        
        # 2. Calculate Checksum
        checksum = sum(header)
        if payload:
            checksum += sum(payload)
        checksum &= 0xFFFF

        # 3. Send
        logger.debug(f">> CMD {cmd_id:02X} | Len: {len(payload)} | Pay: {payload.hex()[:20]}...")
        self.serial.write(header)
        if payload:
            self.serial.write(payload)
        self.serial.write(struct.pack('<H', checksum))

        # 4. Receive Response
        # Read Magic
        magic = self.serial.read(2)
        if len(magic) < 2:
            raise RuntimeError("Timeout waiting for response magic")
            
        if magic != MAGIC:
            raise RuntimeError(f"Invalid response magic: {magic.hex()}")
        
        # Read Header
        resp_header_data = self.serial.read(6) # Cmd(1) + Flags(1) + Len(4)
        if len(resp_header_data) < 6:
             logger.error("Timeout waiting for header")
             raise RuntimeError("Timeout waiting for header")

        resp_cmd, resp_flags, resp_len = struct.unpack('<BB I', resp_header_data)
        logger.debug(f"<< CMD {resp_cmd:02X} | Flags: {resp_flags:02X} | Len: {resp_len}")

        # Read Payload
        resp_payload = b''
        if resp_len > 0:
            resp_payload = self.serial.read(resp_len)
            if len(resp_payload) != resp_len:
                logger.error(f"Timeout waiting for payload. Expected {resp_len}, got {len(resp_payload)}")
                raise RuntimeError(f"Timeout waiting for payload. Expected {resp_len}, got {len(resp_payload)}")
        
        # Read Checksum
        resp_checksum_data = self.serial.read(2)
        if len(resp_checksum_data) < 2:
            logger.error("Timeout waiting for checksum")
            raise RuntimeError("Timeout waiting for checksum")
            
        resp_checksum = struct.unpack('<H', resp_checksum_data)[0]

        # Verify Checksum (Optional but recommended)
        # ...

        # Check for Error Flag
        if resp_flags == 0x02:
            # Error packet
            err_code = struct.unpack('<I', resp_payload)[0] if len(resp_payload) >= 4 else -1
            logger.error(f"Device returned error: {err_code}")
            raise RuntimeError(f"Device returned error: {err_code}")

        return resp_payload

    def ping(self, data: bytes = b'\xCA\xFE\xBA\xBE') -> bool:
        try:
            logger.debug(f"Pinging {self.port}...")
            resp = self._send_packet(CMD_PING, data)
            logger.debug(f"Ping Response: {resp.hex()}")
            return resp == data
        except Exception as e:
            logger.debug(f"Ping failed: {e}")
            return False

    def allocate(self, size: int, caps: int, alignment: int) -> int:
        """
        Allocate memory on the device.
        
        Args:
            size: Size in bytes
            caps: Memory capabilities (MALLOC_CAP_*)
            alignment: Alignment requirement
            
        Returns:
            int: Address of allocated memory
        """
        # Struct: size(4), caps(4), alignment(4)
        payload = struct.pack('<I I I', size, caps, alignment)
        
        logger.log(INFO_VERBOSE, f"Allocating {size} bytes (caps={caps}, align={alignment})")
        resp = self._send_packet(CMD_ALLOC, payload)
        
        if len(resp) < 8:
            raise RuntimeError("Invalid response length for ALLOC")
            
        addr, err = struct.unpack('<I I', resp)
        if err != 0:
            logger.error(f"Wrapper: Allocation Failed! requested_size={size}")
            logger.error("Tip: Check if available memory is sufficient.")
            try:
                stats = self.get_heap_info()
                logger.info("[Heap Status]")
                for k, v in stats.items():
                    logger.info(f"  {k}: {v}")
            except:
                pass
            raise MemoryError(f"Allocation failed on device. Error: {err}")
            
        # Track allocation
        self.allocations[addr] = {
            'size': size,
            'caps': caps,
            'align': alignment
        }
        
        logger.debug(f"Allocated {size} bytes at 0x{addr:08X}")
        return addr

    def free(self, address: int):
        if address not in self.allocations:
            raise ValueError(f"Address 0x{address:08X} not tracked in allocation table")

        # Send Free Command
        payload = struct.pack('<I', address)
        self._send_packet(CMD_FREE, payload)
        
        # Remove from tracking
        del self.allocations[address]
        logger.debug(f"Freed memory at 0x{address:08X}")

    def write_memory(self, address: int, data: bytes):
        # Validation
        end_addr = address + len(data)
        valid = False
        for start, info in self.allocations.items():
            alloc_end = start + info['size']
            if start <= address and end_addr <= alloc_end:
                valid = True
                break
        
        if not valid:
            logger.error(f"Segmentation Fault: Write to 0x{address:08X} out of bounds")
            raise PermissionError(f"Segmentation Fault: Write to 0x{address:08X} out of bounds")

        # Chunking might be needed for large writes, but protocol supports arbitrary len
        # Let's assume USB buffer is handled by OS/Driver.
        logger.log(INFO_VERBOSE, f"Writing {len(data)} bytes to 0x{address:08X}")
        payload = struct.pack('<I', address) + data
        self._send_packet(CMD_WRITE_MEM, payload)

    def read_memory(self, address: int, size: int) -> bytes:
        # Validation
        end_addr = address + size
        valid = False
        for start, info in self.allocations.items():
            alloc_end = start + info['size']
            if start <= address and end_addr <= alloc_end:
                valid = True
                break
        
        if not valid:
            logger.error(f"Segmentation Fault: Read from 0x{address:08X} out of bounds")
            raise PermissionError(f"Segmentation Fault: Read from 0x{address:08X} out of bounds")

        logger.log(INFO_VERBOSE, f"Reading {size} bytes from 0x{address:08X}")
        payload = struct.pack('<I I', address, size)
        return self._send_packet(CMD_READ_MEM, payload)

    def execute(self, address: int) -> int:
        # Validation
        valid = False
        for start, info in self.allocations.items():
            alloc_end = start + info['size']
            if start <= address < alloc_end:
                # Check EXEC cap (bit 0 of caps usually, or MALLOC_CAP_EXEC)
                # For now assume user passes correct caps mask. 
                # Let's say MALLOC_CAP_EXEC is 1 (it's actually bit 0 in IDF usually, but let's check header)
                # Actually, we just check if 'caps' was non-zero or specific flag?
                # User passes raw caps. Let's assume if they asked for EXEC, they passed it.
                # We can just check if it exists for now.
                valid = True
                break
        
        if not valid:
            logger.error(f"Segmentation Fault: Execute at 0x{address:08X} not in valid region")
            raise PermissionError(f"Segmentation Fault: Execute at 0x{address:08X} not in valid region")

        logger.log(INFO_VERBOSE, f"Executing at 0x{address:08X}")
        payload = struct.pack('<I', address)
        resp = self._send_packet(CMD_EXEC, payload)
        
        ret_val = struct.unpack('<I', resp)[0]
        logger.debug(f"Execution finished. Return Value: {ret_val}")
        return ret_val

    def get_heap_info(self) -> Dict[str, int]:
        """
        Get heap memory statistics from the device.
        
        Returns:
            dict: {
                'free_spiram': int,
                'total_spiram': int,
                'free_internal': int,
                'total_internal': int
            }
        """
        resp = self._send_packet(CMD_HEAP_INFO, b'')
        
        if len(resp) < 16:
             raise RuntimeError("Invalid response length for HEAP_INFO")
             
        free_spiram, total_spiram, free_internal, total_internal = struct.unpack('<IIII', resp)
        
        return {
            'free_spiram': free_spiram,
            'total_spiram': total_spiram,
            'free_internal': free_internal,
            'total_internal': total_internal
        }
