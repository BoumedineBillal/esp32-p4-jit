import yaml
import tempfile
import os
import glob

from .compiler import Compiler
from .linker_gen import LinkerGenerator
from .binary_processor import BinaryProcessor
from .symbol_extractor import SymbolExtractor
from .validator import Validator
from .binary_object import BinaryObject
from .wrapper_builder import WrapperBuilder


class Builder:
    """
    Main builder class for ESP32-P4 dynamic code loading with multi-file support.
    
    Usage:
        builder = Builder(config='config/toolchain.yaml')
        binary = builder.build(
            source='sources/main.c',    # Entry file
            entry_point='main',         # Entry function
            base_address=0x40800000
        )
        
    The builder automatically discovers and compiles all source files
    in the same directory as the specified source file.
    """
    
    def __init__(self, config_path='config/toolchain.yaml'):
        """
        Initialize builder with configuration.
        
        Args:
            config_path (str): Path to YAML configuration file
        """
        self.config = self._load_config(config_path)
        self.compiler = Compiler(self.config)
        
        template_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'templates', 'linker.ld.template'
        )
        self.linker_gen = LinkerGenerator(template_path)
        
        self.processor = BinaryProcessor(self.config)
        self.extractor = SymbolExtractor(self.config)
        self.validator = Validator(self.config)
        
        self.temp_dir = tempfile.mkdtemp(prefix='esp32_build_')
        
        # Add wrapper builder for automatic wrapper generation
        self.wrapper = WrapperBuilder(self, self.config)
        
    def _load_config(self, config_path):
        """Load YAML configuration file."""
        if not os.path.isabs(config_path):
            base_dir = os.path.dirname(os.path.dirname(__file__))
            config_path = os.path.join(base_dir, config_path)
            
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
            
    def _parse_address(self, address):
        """Parse address from int or hex string."""
        if isinstance(address, int):
            return address
        elif isinstance(address, str):
            return int(address, 16 if address.startswith('0x') else 10)
        else:
            raise ValueError(f"Invalid address type: {type(address)}")
    
    def _discover_source_files(self, source_dir):
        """
        Discover all compilable source files in directory.
        
        Args:
            source_dir (str): Directory to scan
            
        Returns:
            list: List of absolute paths to source files
        """
        compile_extensions = self.config['extensions']['compile'].keys()
        discovered_files = []
        
        for ext in compile_extensions:
            pattern = os.path.join(source_dir, f'*{ext}')
            found = glob.glob(pattern)
            discovered_files.extend(found)
        
        # Sort for deterministic build order
        discovered_files.sort()
        
        return discovered_files
            
    def build(self, source, entry_point, base_address, 
              optimization=None, output_dir='build', use_firmware_elf=False):
        """
        Build position-specific binary from multiple source files.
        
        The builder automatically discovers and compiles all source files
        in the same directory as the specified source file.
        
        Args:
            source (str): Path to entry source file (determines directory to scan)
            entry_point (str): Entry point function name
            base_address (int or str): Base address (int or hex string)
            optimization (str): Optimization level ('O0', 'O1', 'O2', 'O3', 'Os')
            output_dir (str): Output directory for build artifacts
            use_firmware_elf (bool): Whether to link against firmware ELF symbols (default: False)
            
        Returns:
            BinaryObject: Object containing binary and metadata with methods
        """
        if optimization is None:
            optimization = self.config['compiler']['optimization']
            
        base_addr = self._parse_address(base_address)
        
        # Validate inputs
        self.validator.validate_source(source)
        self.validator.validate_entry_point(entry_point)
        self.validator.validate_address(base_addr)
        
        # Derive source directory from entry file
        source_path = os.path.abspath(source)
        source_dir = os.path.dirname(source_path)
        
        # Discover all source files in directory
        discovered_files = self._discover_source_files(source_dir)
        
        if not discovered_files:
            raise ValueError(
                f"No compilable source files found in {source_dir}\n"
                f"Supported extensions: {list(self.config['extensions']['compile'].keys())}"
            )
        
        print(f"Discovered {len(discovered_files)} source file(s):")
        for src in discovered_files:
            print(f"  - {os.path.basename(src)}")
        
        # Compile each source file to object file
        obj_files = []
        for src_file in discovered_files:
            basename = os.path.basename(src_file)
            name_only = os.path.splitext(basename)[0]
            obj_path = os.path.join(self.temp_dir, f'{name_only}.o')
            
            print(f"Compiling {basename}...", end=' ')
            
            try:
                self.compiler.compile(
                    source=src_file,
                    output=obj_path,
                    optimization=optimization
                )
                obj_files.append(obj_path)
                print("✓")
            except RuntimeError as e:
                print("✗")
                raise e
        
        # Generate linker script
        linker_script = self.linker_gen.generate(
            entry_point=entry_point,
            base_address=base_addr,
            memory_size=self.config['memory']['max_size']
        )
        
        # Link all object files
        print(f"Linking {len(obj_files)} object file(s)...", end=' ')
        elf_file = self.compiler.link(
            obj_files=obj_files,
            linker_script=linker_script,
            output=os.path.join(self.temp_dir, 'output.elf'),
            use_firmware_elf=use_firmware_elf
        )
        print("✓")
        
        # Extract binary
        raw_bin = self.compiler.extract_binary(
            elf_file=elf_file,
            output=os.path.join(self.temp_dir, 'output.bin')
        )
        
        # Process sections and symbols
        sections = self.processor.extract_sections(elf_file)
        padded_bin = self.processor.pad_bss(raw_bin, sections)
        symbols = self.extractor.extract_all_symbols(elf_file)
        entry_addr = self.extractor.get_function_address(elf_file, entry_point)
        
        if entry_addr is None:
            raise ValueError(f"Entry point '{entry_point}' not found in compiled binary")
        
        self.validator.validate_output(sections, base_addr)
        
        return BinaryObject(
            binary_data=padded_bin,
            config=self.config,
            elf_path=elf_file,
            base_address=base_addr,
            entry_point=entry_point,
            entry_address=entry_addr,
            sections=sections,
            symbols=symbols,
            output_dir=output_dir
        )
