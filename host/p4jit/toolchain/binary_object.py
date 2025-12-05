import json
import shutil
import subprocess
import os
from ..utils.logger import setup_logger, INFO_VERBOSE, logging

logger = setup_logger(__name__)

class BinaryObject:
    """
    Result object containing binary and all metadata.
    Provides methods for saving, inspecting, and using the binary.
    """
    
    def __init__(self, binary_data, config, elf_path, base_address, 
                 entry_point, entry_address, sections, symbols, output_dir):
        self._data = binary_data
        self._config = config
        self._elf_path = elf_path
        self._base_address = base_address
        self._entry_point = entry_point
        self._entry_address = entry_address
        self._sections = sections
        self._symbols = symbols
        self._sections = sections
        self._symbols = symbols
        self._output_dir = output_dir
        self.metadata = {} # Extra metadata (e.g. from wrapper)
        
        # Build full path to objdump
        toolchain_path = config['toolchain']['path']
        prefix = config['toolchain']['prefix']
        self._objdump = os.path.join(toolchain_path, f"{prefix}-objdump")
        
    @property
    def data(self):
        """Raw binary data as bytes."""
        return self._data
        
    @property
    def total_size(self):
        """Total size including BSS padding."""
        return len(self._data)
        
    @property
    def base_address(self):
        """Base load address."""
        return self._base_address
        
    @property
    def entry_point(self):
        """Entry point function name."""
        return self._entry_point
        
    @property
    def entry_address(self):
        """Entry point address."""
        return self._entry_address
        
    @property
    def sections(self):
        """Dictionary of section info."""
        return self._sections
        
    @property
    def functions(self):
        """List of all functions with addresses."""
        return [s for s in self._symbols if s.get('type') == 'FUNC']
        
    def save_bin(self, path):
        """Save binary to file."""
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
        with open(path, 'wb') as f:
            f.write(self._data)
            
    def save_elf(self, path):
        """Copy ELF file to specified path."""
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
        shutil.copy(self._elf_path, path)
        
    def save_metadata(self, path):
        """Save metadata as JSON."""
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
        metadata = self.get_metadata_dict()
        with open(path, 'w') as f:
            json.dump(metadata, f, indent=2)
            
    def disassemble(self, output=None, source_intermix=True):
        """
        Disassemble binary.
        """
        cmd = [self._objdump, '-d']
        if source_intermix:
            cmd.append('-S')
        cmd.append(self._elf_path)
        
        logger.log(INFO_VERBOSE, f"Disassembling {os.path.basename(self._elf_path)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if output:
            os.makedirs(os.path.dirname(output) if os.path.dirname(output) else '.', exist_ok=True)
            with open(output, 'w') as f:
                f.write(result.stdout)
            logger.info(f"Disassembly saved to {output}")
        else:
            logger.info(result.stdout)
            
    def print_sections(self):
        """Print section information."""
        logger.info("Sections:")
        for name, info in self._sections.items():
            logger.info(f"  {name:20s} 0x{info['address']:08x}  {info['size']:6d} bytes")
            
    def print_symbols(self):
        """Print symbol table."""
        logger.info("Functions:")
        for func in self.functions:
            logger.info(f"  {func['name']:30s} 0x{func['address']:08x}  {func['size']:4d} bytes")
            
    def print_memory_map(self):
        """Print visual memory map with alignment padding."""
        logger.info(f"Memory Map (Base: 0x{self._base_address:08x}):")
        logger.info("  " + "─" * 60)
        
        current_offset = 0
        
        for name, info in sorted(self._sections.items(), key=lambda x: x[1]['address']):
            offset = info['address'] - self._base_address
            size = info['size']
            
            # Print the section
            logger.info(f"  {offset:6d}  │ {name:12s} {size:6d} bytes")
            
            # Check if padding is needed after this section
            if size % 4 != 0:
                padding = 4 - (size % 4)
                padding_offset = offset + size
                logger.info(f"  {padding_offset:6d}  │ [padding]    {padding:6d} bytes")
        
        logger.info("  " + "─" * 60)
        logger.info(f"  Total: {self.total_size} bytes")
        
    def get_data(self):
        """Get raw binary data as bytes."""
        return self._data
        
    def get_metadata_dict(self):
        """Get metadata as dictionary."""
        return {
            'entry_point': self._entry_point,
            'entry_address': f"0x{self._entry_address:08x}",
            'base_address': f"0x{self._base_address:08x}",
            'total_size': self.total_size,
            'sections': {
                name: {
                    'address': f"0x{info['address']:08x}",
                    'size': info['size'],
                    'type': info['type']
                }
                for name, info in self._sections.items()
            },
            'functions': [
                {
                    'name': f['name'],
                    'address': f"0x{f['address']:08x}",
                    'size': f['size']
                }
                for f in self.functions
            ]
        }
        
    def get_function_address(self, name):
        """Get address of a specific function."""
        for func in self.functions:
            if func['name'] == name:
                return func['address']
        return None
        
    def validate(self):
        """Validate binary integrity."""
        if self._base_address % 4 != 0:
            raise ValueError("Base address not 4-byte aligned")
            
        if self.total_size > 128 * 1024:
            raise ValueError("Binary exceeds 128KB limit")
            
        if self.get_function_address(self._entry_point) is None:
            raise ValueError(f"Entry point '{self._entry_point}' not found")
            
        return True
