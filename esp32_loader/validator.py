class Validator:
    """Validates binary and memory configurations."""
    
    def __init__(self, config):
        self.config = config
        self.max_size = self._parse_size(config['memory']['max_size'])
        self.alignment = config['memory']['alignment']
        
    def _parse_size(self, size_str):
        """Parse size string like '128K' to bytes."""
        size_str = size_str.strip().upper()
        
        if size_str.endswith('K'):
            return int(size_str[:-1]) * 1024
        elif size_str.endswith('M'):
            return int(size_str[:-1]) * 1024 * 1024
        else:
            return int(size_str)
            
    def validate_address(self, address):
        """
        Validate memory address.
        
        Args:
            address (int): Memory address
            
        Raises:
            ValueError: If address is invalid
        """
        if address % self.alignment != 0:
            raise ValueError(f"Address 0x{address:08x} not {self.alignment}-byte aligned")
            
        if address < 0x30100000 and address >= 0x50000000:
            raise ValueError(f"Address 0x{address:08x} outside valid memory range")
            
    def validate_source(self, source_file):
        """
        Validate source file exists.
        
        Args:
            source_file (str): Path to source file
            
        Raises:
            FileNotFoundError: If source file doesn't exist
        """
        import os
        if not os.path.exists(source_file):
            raise FileNotFoundError(f"Source file not found: {source_file}")
            
    def validate_entry_point(self, entry_point):
        """
        Validate entry point name.
        
        Args:
            entry_point (str): Entry point function name
            
        Raises:
            ValueError: If entry point name is invalid
        """
        if not entry_point:
            raise ValueError("Entry point cannot be empty")
            
        if not entry_point.isidentifier():
            raise ValueError(f"Invalid entry point name: {entry_point}")
            
    def validate_output(self, sections, base_address):
        """
        Validate generated output.
        
        Args:
            sections (dict): Section information
            base_address (int): Base address
            
        Raises:
            ValueError: If output is invalid
        """
        total_size = 0
        
        for name, info in sections.items():
            if info['address'] < base_address:
                raise ValueError(f"Section {name} below base address")
                
            total_size += info['size']
            
        if total_size > self.max_size:
            raise ValueError(f"Total size {total_size} exceeds max {self.max_size}")
