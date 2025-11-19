import os


class LinkerGenerator:
    """Generates linker scripts from templates."""
    
    def __init__(self, template_path):
        """
        Initialize linker generator.
        
        Args:
            template_path (str): Path to linker script template
        """
        with open(template_path, 'r') as f:
            self.template = f.read()
            
    def generate(self, entry_point, base_address, memory_size, output_path=None):
        """
        Generate linker script from template.
        
        Args:
            entry_point (str): Entry point function name
            base_address (int): Base memory address
            memory_size (str): Memory size (e.g., '128K')
            output_path (str): Optional path to save generated script
            
        Returns:
            str: Path to generated linker script
        """
        script_content = self.template.format(
            ENTRY_POINT=entry_point,
            BASE_ADDRESS=f'0x{base_address:08x}',
            MEMORY_SIZE=memory_size
        )
        
        if output_path is None:
            import tempfile
            fd, output_path = tempfile.mkstemp(suffix='.ld', prefix='linker_')
            os.close(fd)
            
        with open(output_path, 'w') as f:
            f.write(script_content)
            
        return output_path
