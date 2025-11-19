import subprocess
import re
import os


class BinaryProcessor:
    """Handles binary post-processing operations."""
    
    def __init__(self, config):
        self.config = config
        toolchain_path = config['toolchain']['path']
        prefix = config['toolchain']['prefix']
        self.readelf = os.path.join(toolchain_path, f"{prefix}-readelf")
        
    def extract_sections(self, elf_file):
        """
        Extract section information from ELF file.
        
        Args:
            elf_file (str): Path to ELF file
            
        Returns:
            dict: Section information
                {
                    '.text': {'address': 0x40800000, 'size': 152, 'type': 'PROGBITS'},
                    '.rodata': {'address': 0x40800098, 'size': 16, 'type': 'PROGBITS'},
                    '.data': {'address': 0x408000a8, 'size': 4, 'type': 'PROGBITS'},
                    '.bss': {'address': 0x408000ac, 'size': 4, 'type': 'NOBITS'}
                }
        """
        cmd = [self.readelf, '-S', elf_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Section extraction failed:\n{result.stderr}")
            
        sections = {}
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            
            if not line or line.startswith('[') and 'Name' in line:
                continue
                
            match = re.search(r'\[\s*\d+\]\s+(\.[\w.]+)\s+(\w+)\s+([0-9a-f]+)\s+[0-9a-f]+\s+([0-9a-f]+)', line)
            
            if match:
                name = match.group(1)
                sect_type = match.group(2)
                address = int(match.group(3), 16)
                size = int(match.group(4), 16)
                
                if name in ['.text', '.rodata', '.data', '.bss']:
                    sections[name] = {
                        'address': address,
                        'size': size,
                        'type': sect_type
                    }
                    
        return sections
        
    def pad_bss(self, binary_data, sections):
        """
        Pad binary with zeros for alignment and BSS sections.
        
        Args:
            binary_data (bytes): Raw binary data from ELF
            sections (dict): Section information
            
        Returns:
            bytes: Binary with alignment padding and BSS appended
        """
        # First, align binary to 4-byte boundary
        alignment_padding = (4 - (len(binary_data) % 4)) % 4
        
        # Then add BSS size
        bss_size = sum(
            s['size'] for s in sections.values() 
            if s['type'] == 'NOBITS'
        )
        
        total_padding = alignment_padding + bss_size
        return binary_data + b'\x00' * total_padding
