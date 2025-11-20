import re
import os
from pycparser import c_parser, c_ast, parse_file


class SignatureParser:
    """
    Parse C function signatures from source files.
    Extracts function name, return type, and parameters with type classification.
    """
    
    def __init__(self, source_file):
        self.source_file = source_file
        
    def parse_function(self, function_name):
        """
        Parse function signature from source file.
        
        Args:
            function_name: Name of function to parse
            
        Returns:
            dict: {
                'name': str,
                'return_type': str,
                'parameters': [{'name': str, 'type': str, 'category': str}]
            }
            
        Raises:
            ValueError: If function not found or parsing fails
        """
        with open(self.source_file, 'r') as f:
            source_code = f.read()
        
        # Remove comments before parsing
        source_code = self._remove_comments(source_code)
        
        parser = c_parser.CParser()
        
        try:
            ast = parser.parse(source_code, filename=self.source_file)
        except Exception:
            ast = self._parse_with_fake_headers(source_code)
        
        for node in ast.ext:
            if isinstance(node, c_ast.FuncDef):
                if node.decl.name == function_name:
                    return self._extract_signature(node)
        
        raise ValueError(f"Function '{function_name}' not found in {self.source_file}")
    
    def extract_typedefs(self):
        """
        Extract all typedef declarations from source file.
        
        Returns:
            list: List of typedef strings (e.g., ['typedef int int32_t;', ...])
        """
        with open(self.source_file, 'r') as f:
            source_code = f.read()
        
        # Remove comments
        source_code = self._remove_comments(source_code)
        
        parser = c_parser.CParser()
        
        try:
            ast = parser.parse(source_code, filename=self.source_file)
        except Exception:
            ast = self._parse_with_fake_headers(source_code)
        
        typedefs = []
        
        for node in ast.ext:
            if isinstance(node, c_ast.Typedef):
                typedef_str = self._typedef_to_string(node)
                if typedef_str:
                    typedefs.append(typedef_str)
        
        return typedefs
    
    def _typedef_to_string(self, typedef_node):
        """Convert typedef AST node to string."""
        try:
            type_str = self._get_type_string(typedef_node.type)
            name = typedef_node.name
            return f"typedef {type_str} {name};"
        except:
            return None
    
    def _remove_comments(self, source_code):
        """Remove C and C++ style comments from source code."""
        # Remove C++ style comments (//)
        source_code = re.sub(r'//.*?$', '', source_code, flags=re.MULTILINE)
        
        # Remove C style comments (/* */)
        source_code = re.sub(r'/\*.*?\*/', '', source_code, flags=re.DOTALL)
        
        return source_code
    
    def _parse_with_fake_headers(self, source_code):
        """Parse with fake libc headers to handle typedefs."""
        fake_includes = """
typedef int int8_t;
typedef int int16_t;
typedef int int32_t;
typedef int int64_t;
typedef unsigned int uint8_t;
typedef unsigned int uint16_t;
typedef unsigned int uint32_t;
typedef unsigned int uint64_t;
typedef unsigned int size_t;
typedef int esp_err_t;
        """
        
        modified_source = fake_includes + "\n" + source_code
        parser = c_parser.CParser()
        
        return parser.parse(modified_source, filename='<modified>')
    
    def _extract_signature(self, func_node):
        """Extract signature information from function AST node."""
        func_decl = func_node.decl
        
        return_type = self._get_type_string(func_decl.type.type)
        
        parameters = []
        if func_decl.type.args:
            for param in func_decl.type.args.params:
                param_info = self._extract_parameter(param)
                parameters.append(param_info)
        
        return {
            'name': func_decl.name,
            'return_type': return_type,
            'parameters': parameters
        }
    
    def _extract_parameter(self, param_node):
        """Extract parameter information from AST node."""
        param_type = self._get_type_string(param_node.type)
        param_name = param_node.name if param_node.name else 'unnamed'
        category = self.classify_parameter(param_type)
        
        return {
            'name': param_name,
            'type': param_type,
            'category': category
        }
    
    def _get_type_string(self, type_node):
        """Convert type AST node to string representation."""
        if isinstance(type_node, c_ast.TypeDecl):
            type_name = self._get_base_type_name(type_node.type)
            return type_name
        elif isinstance(type_node, c_ast.PtrDecl):
            inner_type = self._get_type_string(type_node.type)
            return inner_type + '*'
        elif isinstance(type_node, c_ast.ArrayDecl):
            inner_type = self._get_type_string(type_node.type)
            return inner_type + '[]'
        else:
            return 'unknown'
    
    def _get_base_type_name(self, type_node):
        """Get base type name from type node."""
        if isinstance(type_node, c_ast.IdentifierType):
            return ' '.join(type_node.names)
        elif isinstance(type_node, c_ast.Struct):
            return f'struct {type_node.name}' if type_node.name else 'struct'
        else:
            return 'unknown'
    
    def classify_parameter(self, type_str):
        """
        Classify parameter as 'value' or 'pointer'.
        
        Args:
            type_str: Type string (e.g., 'int32_t', 'float*', 'char[]')
            
        Returns:
            str: 'value' or 'pointer'
        """
        if '*' in type_str or '[]' in type_str:
            return 'pointer'
        else:
            return 'value'
    
    def validate_parameter_count(self, param_count, max_params):
        """
        Validate parameter count fits in args array.
        
        Args:
            param_count: Number of parameters
            max_params: Maximum allowed parameters
            
        Raises:
            ValueError: If param_count > max_params
        """
        if param_count > max_params:
            raise ValueError(
                f"Function has {param_count} parameters but args array "
                f"supports maximum {max_params} arguments"
            )
