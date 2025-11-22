import re
import os
import sys
from pycparser import c_parser, c_ast

class SignatureParser:
    """
    Parses C source files to extract function signatures using pycparser.
    Uses a regex heuristic to extract the function definition line and 
    prepends standard typedefs from a config file to ensure parsing success.
    """
    
    def __init__(self, source_file):
        self.source_file = source_file
        self.current_function = None
        self.std_types = self._load_std_types()
        
    def _load_std_types(self):
        """Load standard typedefs from config file."""
        # Assuming config is at ../config/std_types.h relative to this file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, 'config', 'std_types.h')
        
        try:
            with open(config_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Warning: Standard types config not found at {config_path}")
            return ""

    def parse_function(self, function_name):
        """
        Parse function signature from source file.
        
        Args:
            function_name (str): Name of function to find
            
        Returns:
            dict: Function signature details
        """
        self.current_function = function_name
        
        with open(self.source_file, 'r') as f:
            source_code = f.read()
            
        # Extract the signature string using regex heuristic
        signature_str = self._extract_signature_string(source_code, function_name)
        
        if not signature_str:
             raise ValueError(f"Function '{function_name}' not found in {self.source_file}")
             
        # Combine standard types and the extracted signature
        full_code = self.std_types + "\n" + signature_str
        
        # Save for debugging
        self._save_debug_output(full_code)
        
        # Parse with pycparser
        parser = c_parser.CParser()
        try:
            ast = parser.parse(full_code, filename='<extracted_signature>')
        except Exception as e:
            print(f"[DEBUG] Parse Error: {e}")
            print(f"[DEBUG] Code being parsed:\n{full_code}")
            raise
            
        # Find the function declaration in the AST
        # It will be the last node usually, or we search for it
        for node in ast.ext:
            if isinstance(node, c_ast.Decl) and node.name == function_name:
                 # Wrap in fake FuncDef for extraction logic compatibility
                 fake_def = c_ast.FuncDef(decl=node, param_decls=None, body=None)
                 return self._extract_signature_from_ast(fake_def)
            elif isinstance(node, c_ast.FuncDef) and node.decl.name == function_name:
                 return self._extract_signature_from_ast(node)
                 
        raise ValueError(f"Parsed successfully but function '{function_name}' node not found in AST")

    def _extract_signature_string(self, source_code, func_name):
        """
        Extract the function signature string (prototype) from source code.
        Strategy:
        1. Find the line containing the function name.
        2. Extract text before the name (return type).
        3. Extract text after the name (argument list) up to the closing parenthesis.
        4. Construct a clean prototype: "ReturnType FunctionName(Args);"
        """
        lines = source_code.splitlines()
        
        for i, line in enumerate(lines):
            if func_name in line:
                # Check if this looks like a definition start
                
                # Find start of name
                idx = line.find(func_name)
                if idx == -1: continue
                
                # Check if it's a call or definition
                # Look ahead for (
                rest = line[idx + len(func_name):].strip()
                if not rest.startswith('('):
                    continue
                    
                # It matches "Name("
                # Now capture the return type (preceding text)
                return_type_part = line[:idx].strip()
                
                # Now capture arguments. They might span multiple lines.
                # We start from the opening (
                
                combined_text = source_code[source_code.find(line):] # Start from this line
                
                # Simple parenthesis counter
                balance = 0
                args_end_idx = -1
                
                # Find the first ( relative to combined_text
                start_paren = combined_text.find('(')
                
                if start_paren == -1: continue

                for j, char in enumerate(combined_text[start_paren:]):
                    if char == '(':
                        balance += 1
                    elif char == ')':
                        balance -= 1
                        if balance == 0:
                            args_end_idx = start_paren + j
                            break
                
                if args_end_idx != -1:
                    args_part = combined_text[start_paren:args_end_idx+1]
                    
                    # Construct prototype
                    prototype_str = f"{return_type_part} {func_name}{args_part};"
                    print(f"[DEBUG] Extracted Signature: {prototype_str}")
                    return prototype_str
                    
        return None

    def _save_debug_output(self, content):
        """Save the parsed content to a file for debugging."""
        try:
            source_dir = os.path.dirname(os.path.abspath(self.source_file))
            test_root = os.path.dirname(source_dir) # Go up one level from 'source'
            build_dir = os.path.join(test_root, 'build')
            
            if not os.path.exists(build_dir):
                os.makedirs(build_dir)
                
            debug_path = os.path.join(build_dir, 'extracted_signature.c')
            with open(debug_path, 'w') as f:
                f.write(content)
            print(f"[DEBUG] Parsing input saved to: {debug_path}")
        except Exception as e:
            print(f"[DEBUG] Failed to save debug output: {e}")

    def _extract_signature_from_ast(self, func_node):
        """Extract signature information from function AST node."""
        func_decl = func_node.decl
        
        return_type = self._get_type_string(func_decl.type.type)
        
        parameters = []
        if func_decl.type.args:
            for param in func_decl.type.args.params:
                # Handle 'void' parameter (e.g. void foo(void))
                # pycparser represents this as a parameter with type 'void' and no name
                param_type = self._get_type_string(param.type)
                if param_type == 'void':
                    continue
                    
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
        """
        if '*' in type_str or '[]' in type_str:
            return 'pointer'
        else:
            return 'value'
    
    def validate_parameter_count(self, param_count, max_params):
        """
        Validate parameter count fits in args array.
        """
        if param_count > max_params:
            raise ValueError(
                f"Function has {param_count} parameters but args array "
                f"supports maximum {max_params} arguments"
            )
