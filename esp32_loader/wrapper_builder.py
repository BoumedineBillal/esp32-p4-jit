import os
from .signature_parser import SignatureParser
from .wrapper_generator import WrapperGenerator
from .header_generator import HeaderGenerator
from .metadata_generator import MetadataGenerator


class WrapperBuilder:
    """
    Orchestrate automatic wrapper generation and building.
    Uses existing Builder to compile generated wrapper.
    """
    
    def __init__(self, builder, config):
        self.builder = builder
        self.config = config
    
    def build_with_wrapper(self, source, function_name, base_address, 
                          arg_address, output_dir='build', use_firmware_elf=False):
        """
        Build function with automatic wrapper generation.
        
        Args:
            source: Original source file containing function
            function_name: Name of function to wrap
            base_address: Code load address
            arg_address: I/O region base address for arguments
            output_dir: Output directory for binary and metadata
            
        Returns:
            BinaryObject: Built binary with wrapper
            
        Raises:
            ValueError: If function not found or args exceed array size
        """
        print(f"Wrapper Builder: Generating wrapper for '{function_name}'")
        print(f"  Source: {source}")
        print(f"  Code base: 0x{base_address:08x}")
        print(f"  Args base: 0x{arg_address:08x}")
        print()
        
        # Parse function signature
        parser = SignatureParser(source)
        signature = parser.parse_function(function_name)
        
        print(f"Function signature parsed:")
        print(f"  Name: {signature['name']}")
        print(f"  Return: {signature['return_type']}")
        print(f"  Parameters: {len(signature['parameters'])}")
        for idx, param in enumerate(signature['parameters']):
            print(f"    [{idx}] {param['type']} {param['name']} ({param['category']})")
        print()
        
        # Validate argument count
        args_array_size = self.config['wrapper']['args_array_size']
        max_args = args_array_size - 1
        param_count = len(signature['parameters'])
        
        if param_count > max_args:
            raise ValueError(
                f"Function has {param_count} parameters but args array "
                f"supports max {max_args} (array_size={args_array_size}, "
                f"last slot reserved for return value)"
            )
        
        print(f"Validation passed: {param_count} args fit in array (max {max_args})")
        print()
        
        # Get source directory
        source_dir = os.path.dirname(os.path.abspath(source))
        
        # Generate header file
        print("Generating header file...")
        header_gen = HeaderGenerator(source, signature)
        header_path = header_gen.save_header(source_dir)
        print(f"  Generated: {header_path}")
        print()
        
        # Generate wrapper
        print("Generating wrapper...")
        wrapper_gen = WrapperGenerator(self.config, signature, source, arg_address)
        temp_c_path = wrapper_gen.save_wrapper(source_dir)
        print(f"  Generated: {temp_c_path}")
        print()
        
        # Build using existing builder (will discover both files)
        wrapper_entry = self.config['wrapper']['wrapper_entry']
        
        print(f"Building with existing builder...")
        print(f"  Entry point: {wrapper_entry}")
        print()
        
        binary = self.builder.build(
            source=temp_c_path,
            entry_point=wrapper_entry,
            base_address=base_address,
            use_firmware_elf=use_firmware_elf
        )
        
        print()
        print(f"Generating metadata...")
        
        # Generate signature.json
        metadata_gen = MetadataGenerator(
            signature, arg_address, base_address, args_array_size
        )
        signature_path = metadata_gen.save_json(output_dir)
        
        # Attach metadata to binary object
        binary.metadata = metadata_gen.generate_metadata()
        
        print(f"  Generated: {signature_path}")
        print()
        
        return binary
