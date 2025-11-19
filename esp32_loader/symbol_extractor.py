import subprocess
import re
import os


class SymbolExtractor:
    """Extracts symbol information from ELF files."""
    
    def __init__(self, config):
        self.config = config
        toolchain_path = config['toolchain']['path']
        prefix = config['toolchain']['prefix']
        self.readelf = os.path.join(toolchain_path, f"{prefix}-readelf")
        self.nm = os.path.join(toolchain_path, f"{prefix}-nm")
        
    def extract_all_symbols(self, elf_file):
        """
        Extract all symbols from ELF file using nm (most reliable).
        
        Args:
            elf_file (str): Path to ELF file
            
        Returns:
            list: List of symbol dictionaries
        """
        # Use nm with size information
        cmd = [self.nm, '--print-size', '--size-sort', elf_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            # Fallback to basic nm
            cmd = [self.nm, elf_file]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"Symbol extraction failed:\n{result.stderr}")
            
        symbols = []
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            
            # Format can be:
            # address size type name
            # or
            # address type name
            
            if len(parts) >= 3:
                try:
                    address = int(parts[0], 16)
                    
                    # Check if second field is size or type
                    if len(parts) >= 4:
                        # Has size: addr size type name
                        size = int(parts[1], 16)
                        type_char = parts[2]
                        name = ' '.join(parts[3:])
                    else:
                        # No size: addr type name
                        size = 0
                        type_char = parts[1]
                        name = ' '.join(parts[2:])
                    
                    # Convert nm type to symbol type
                    if type_char in ['T', 't']:
                        sym_type = 'FUNC'
                    elif type_char in ['D', 'd', 'B', 'b', 'R', 'r', 'C', 'c']:
                        sym_type = 'OBJECT'
                    else:
                        continue
                    
                    if address != 0 and name:
                        symbols.append({
                            'name': name,
                            'address': address,
                            'size': size,
                            'type': sym_type
                        })
                        
                except (ValueError, IndexError):
                    continue
                    
        return symbols
        
    def get_function_address(self, elf_file, function_name):
        """
        Get address of a specific function.
        
        Args:
            elf_file (str): Path to ELF file
            function_name (str): Name of function to find
            
        Returns:
            int: Address of function, or None if not found
        """
        symbols = self.extract_all_symbols(elf_file)
        
        # Look for exact match
        for symbol in symbols:
            if symbol['name'] == function_name and symbol['type'] == 'FUNC':
                return symbol['address']
        
        # Not found - debug info
        print(f"\n{'='*70}")
        print(f"ERROR: Function '{function_name}' not found in compiled binary")
        print(f"{'='*70}")
        
        funcs = [s for s in symbols if s['type'] == 'FUNC']
        
        if funcs:
            print(f"\nAvailable functions ({len(funcs)}):")
            for symbol in sorted(funcs, key=lambda x: x['address']):
                size_str = f"{symbol['size']:4d}" if symbol['size'] else "   ?"
                print(f"  {symbol['name']:50s} 0x{symbol['address']:08x} ({size_str} bytes)")
        else:
            print("\nNO FUNCTIONS FOUND!")
        
        # Check for partial matches
        matches = [s for s in funcs if function_name.lower() in s['name'].lower()]
        if matches:
            print(f"\nPartial matches for '{function_name}':")
            for symbol in matches:
                print(f"  {symbol['name']}")
        
        print(f"{'='*70}\n")
        
        return None

class SymbolExtractor_origin:
    """Extracts symbol information from ELF files."""
    
    def __init__(self, config):
        self.config = config
        toolchain_path = config['toolchain']['path']
        prefix = config['toolchain']['prefix']
        self.readelf = os.path.join(toolchain_path, f"{prefix}-readelf")
        
    def extract_all_symbols(self, elf_file):
        """
        Extract all symbols from ELF file.
        
        Args:
            elf_file (str): Path to ELF file
            
        Returns:
            list: List of symbol dictionaries
                [
                    {'name': 'compute', 'address': 0x40800000, 'size': 100, 'type': 'FUNC'},
                    {'name': 'data_var', 'address': 0x40800100, 'size': 4, 'type': 'OBJECT'},
                ]
        """
        cmd = [self.readelf, '-s', elf_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Symbol extraction failed:\n{result.stderr}")
            
        symbols = []
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            
            if 'FUNC' in line or 'OBJECT' in line:
                parts = line.split()
                
                if len(parts) >= 8:
                    try:
                        address = int(parts[1], 16)
                        size = int(parts[2])
                        sym_type = parts[3]
                        name = parts[7] if len(parts) > 7 else ''
                        
                        if name and address != 0:
                            symbols.append({
                                'name': name,
                                'address': address,
                                'size': size,
                                'type': sym_type
                            })
                    except (ValueError, IndexError):
                        continue
                        
        return symbols
        
    def get_function_address(self, elf_file, function_name):
        """
        Get address of a specific function.
        
        Args:
            elf_file (str): Path to ELF file
            function_name (str): Name of function to find
            
        Returns:
            int: Address of function, or None if not found
        """
        symbols = self.extract_all_symbols(elf_file)
        
        for symbol in symbols:
            if symbol['name'] == function_name and symbol['type'] == 'FUNC':
                return symbol['address']
                
        return None
