import subprocess
import os


class Compiler:
    """Handles compilation and linking operations with multi-file support."""
    
    def __init__(self, config):
        self.config = config
        self.toolchain_path = config['toolchain']['path']
        self.prefix = config['toolchain']['prefix']
        
        # Build compiler paths from config
        self.compilers = {}
        for name, exe in config['toolchain']['compilers'].items():
            self.compilers[name] = os.path.join(self.toolchain_path, exe)
        
        # Build other tool paths
        self.objcopy = os.path.join(self.toolchain_path, f"{self.prefix}-objcopy")
        self.objdump = os.path.join(self.toolchain_path, f"{self.prefix}-objdump")
        self.readelf = os.path.join(self.toolchain_path, f"{self.prefix}-readelf")
        self.size = os.path.join(self.toolchain_path, f"{self.prefix}-size")
        
    def compile(self, source, output, optimization='O2'):
        """
        Compile source file to object file.
        Automatically selects compiler based on file extension.
        Include path is derived from source file directory.
        
        Args:
            source (str): Path to source file (.c, .cpp, .S, .s, etc.)
            output (str): Path to output object file
            optimization (str): Optimization level
            
        Returns:
            str: Path to compiled object file
        """
        # Get file extension
        ext = os.path.splitext(source)[1]
        
        # Look up compiler from config
        compile_map = self.config['extensions']['compile']
        if ext not in compile_map:
            raise ValueError(
                f"Unknown file extension: {ext}\n"
                f"Supported extensions: {list(compile_map.keys())}"
            )
        
        compiler_name = compile_map[ext]
        compiler_path = self.compilers[compiler_name]
        
        # Derive include directory from source file
        source_dir = os.path.dirname(os.path.abspath(source))
        include_flag = f'-I{source_dir}'
        
        # Build command based on compiler type
        if compiler_name == 'as':
            # Pure assembler - simpler flags
            cmd = [
                compiler_path,
                include_flag,
                source,
                '-o', output
            ]
        else:
            # gcc or g++ - full compilation flags
            arch = self.config['compiler']['arch']
            abi = self.config['compiler']['abi']
            flags = self.config['compiler']['flags']
            
            cmd = [
                compiler_path,
                f'-march={arch}',
                f'-mabi={abi}',
                f'-{optimization}',
                '-g',
                include_flag,
                '-c',
                source,
                '-o', output
            ] + flags
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(
                f"Compilation failed for {os.path.basename(source)}:\n{result.stderr}"
            )
            
        return output
        
    def link(self, obj_files, linker_script, output, use_firmware_elf=False):
        """
        Link multiple object files with custom linker script.
        
        Args:
            obj_files (list): List of object file paths
            linker_script (str): Path to linker script
            output (str): Path to output ELF file
            use_firmware_elf (bool): Whether to link against firmware ELF symbols
            
        Returns:
            str: Path to linked ELF file
        """
        arch = self.config['compiler']['arch']
        abi = self.config['compiler']['abi']
        linker_flags = self.config['linker']['flags']
        firmware_elf = self.config.get('linker', {}).get('firmware_elf')
        
        # Use gcc for linking (works for both C and C++ objects)
        cmd = [
            self.compilers['gcc'],
            f'-march={arch}',
            f'-mabi={abi}',
            f'-T{linker_script}'
        ]
        
        # Add firmware symbols if configured AND enabled
        if use_firmware_elf and firmware_elf:
            # Resolve absolute path relative to config file location if needed
            # But here we assume the user provides a valid path or we handle it in builder
            # For now, let's just pass it.
            cmd.append(f'-Wl,-R,{firmware_elf}')
            
        cmd += obj_files + [
            '-o', output
        ] + linker_flags
        
        if self.config['linker']['garbage_collection']:
            cmd.append('-Wl,--gc-sections')
            
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Linking failed:\n{result.stderr}")
            
        return output
        
    def extract_binary(self, elf_file, output):
        """
        Extract raw binary from ELF file.
        
        Args:
            elf_file (str): Path to ELF file
            output (str): Path to output binary file
            
        Returns:
            bytes: Raw binary data
        """
        cmd = [
            self.objcopy,
            '-O', 'binary',
            elf_file,
            output
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Binary extraction failed:\n{result.stderr}")
            
        with open(output, 'rb') as f:
            return f.read()
