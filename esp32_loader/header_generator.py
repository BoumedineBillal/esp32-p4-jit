import os
from .signature_parser import SignatureParser


class HeaderGenerator:
    """
    Generate header files with typedef declarations and function prototypes.
    """
    
    def __init__(self, source_file, signature_data):
        self.source_file = source_file
        self.signature = signature_data
        self.source_basename = os.path.basename(source_file)
        self.header_name = os.path.splitext(self.source_basename)[0] + '.h'
        
    def parse_typedefs(self):
        """Extract typedefs from source file."""
        parser = SignatureParser(self.source_file)
        return parser.extract_typedefs()
    
    def generate_header(self):
        """Generate complete header file content."""
        parts = []
        
        parts.append(self._generate_header_guard_start())
        parts.append(self._generate_header_comment())
        parts.append(self._generate_typedefs())
        parts.append(self._generate_function_declaration())
        parts.append(self._generate_header_guard_end())
        
        return '\n'.join(parts)
    
    def _generate_header_guard_start(self):
        """Generate header guard start."""
        guard_name = self.header_name.upper().replace('.', '_')
        return f"""#ifndef {guard_name}
#define {guard_name}
"""
    
    def _generate_header_comment(self):
        """Generate header comment."""
        func_name = self.signature['name']
        return f"""// Auto-generated header for {func_name}
// Source: {self.source_basename}
"""
    
    def _generate_typedefs(self):
        """Generate typedef section."""
        typedefs = self.parse_typedefs()
        
        if not typedefs:
            return ""
        
        lines = ["// Extracted typedefs"]
        lines.extend(typedefs)
        lines.append("")
        
        return '\n'.join(lines)
    
    def _generate_function_declaration(self):
        """Generate function declaration (prototype)."""
        func_name = self.signature['name']
        return_type = self.signature['return_type']
        
        params = []
        for param in self.signature['parameters']:
            param_type = param['type']
            param_name = param['name']
            params.append(f"{param_type} {param_name}")
        
        params_str = ', '.join(params) if params else 'void'
        
        lines = [
            "// Function declaration",
            f"{return_type} {func_name}({params_str});",
            ""
        ]
        
        return '\n'.join(lines)
    
    def _generate_header_guard_end(self):
        """Generate header guard end."""
        guard_name = self.header_name.upper().replace('.', '_')
        return f"""#endif // {guard_name}
"""
    
    def save_header(self, output_dir):
        """
        Save generated header to directory.
        
        Args:
            output_dir: Directory to save header file
            
        Returns:
            str: Path to generated header file
        """
        header_content = self.generate_header()
        
        output_path = os.path.join(output_dir, self.header_name)
        
        with open(output_path, 'w') as f:
            f.write(header_content)
        
        return output_path
