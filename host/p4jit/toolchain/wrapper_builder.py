import os
from .signature_parser import SignatureParser
from .wrapper_generator import WrapperGenerator
from .header_generator import HeaderGenerator
from .metadata_generator import MetadataGenerator
from ..utils.logger import setup_logger, INFO_VERBOSE

logger = setup_logger(__name__)

class WrapperBuilder:
    """
    Orchestrate automatic wrapper generation and building.
    Uses existing Builder to compile generated wrapper.
    """
    
    def __init__(self, builder, config):
        self.builder = builder
        self.config = config
    
    def build_with_wrapper(self, source, function_name, base_address, 
                          arg_address, output_dir=None, use_firmware_elf=True):
        """
        Build function with automatic wrapper generation.
        """
        # Auto-detect start
        if output_dir is None:
             output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(source))), 'build')
        # Auto-detect end

        logger.info(f"Generating wrapper for '{function_name}'")
        logger.debug(f"Wrapper Config: Source={source}, CodeBase=0x{base_address:08x}, ArgsBase=0x{arg_address:08x}, OutputDir={output_dir}")
        
        # Parse function signature
        parser = SignatureParser(source)
        try:
            signature = parser.parse_function(function_name)
        except Exception as e:
            logger.error(f"Failed to parse function signature: {e}")
            raise e
        
        logger.log(INFO_VERBOSE, f"Signature parsed: {signature['name']} -> {signature['return_type']}")
        for idx, param in enumerate(signature['parameters']):
            logger.log(INFO_VERBOSE, f"  Arg[{idx}] {param['type']} {param['name']} ({param['category']})")
        
        # Validate argument count
        args_array_size = self.config['wrapper']['args_array_size']
        max_args = args_array_size - 1
        param_count = len(signature['parameters'])
        
        if param_count > max_args:
            logger.error(f"Parameter count {param_count} exceeds limit {max_args}")
            raise ValueError(
                f"Function has {param_count} parameters but args array "
                f"supports max {max_args} (array_size={args_array_size}, "
                f"last slot reserved for return value)"
            )
        
        logger.debug(f"Validation successful: {param_count} parameters.")
        
        # Get source directory
        source_dir = os.path.dirname(os.path.abspath(source))
        
        # Generate header file
        logger.log(INFO_VERBOSE, "Generating header file...")
        header_gen = HeaderGenerator(source, signature)
        header_path = header_gen.save_header(source_dir)
        logger.debug(f"Generated header: {header_path}")
        
        # Copy std_types.h
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        std_types_src = os.path.join(project_root, 'config', 'std_types.h')
        std_types_dst = os.path.join(source_dir, 'std_types.h')
        
        if os.path.exists(std_types_src):
            import shutil
            shutil.copy2(std_types_src, std_types_dst)
            logger.debug(f"Copied std_types.h to {source_dir}")
        else:
            logger.warning(f"std_types.h not found at {std_types_src}")
            
        # Generate wrapper
        logger.log(INFO_VERBOSE, "Generating wrapper C code...")
        wrapper_gen = WrapperGenerator(self.config, signature, source, arg_address)
        temp_c_path = wrapper_gen.save_wrapper(source_dir)
        logger.debug(f"Generated wrapper: {temp_c_path}")
        
        # Build using existing builder
        wrapper_entry = self.config['wrapper']['wrapper_entry']
        
        logger.info("Building wrapper binary...")
        binary = self.builder.build(
            source=temp_c_path,
            entry_point=wrapper_entry,
            base_address=base_address,
            use_firmware_elf=use_firmware_elf
        )
        
        # Generate metadata
        logger.log(INFO_VERBOSE, "Generating metadata...")
        metadata_gen = MetadataGenerator(
            signature, arg_address, base_address, args_array_size
        )
        signature_path = metadata_gen.save_json(output_dir)
        
        # Attach metadata to binary object
        binary.metadata = metadata_gen.generate_metadata()
        
        logger.info(f"Wrapper build complete. Metadata saved to {signature_path}")
        
        return binary
