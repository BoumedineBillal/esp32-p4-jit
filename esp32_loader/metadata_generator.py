import json
import os


class MetadataGenerator:
    """
    Generate signature.json metadata file with function signature and memory addresses.
    """
    
    def __init__(self, signature_data, arg_address, base_address, args_array_size):
        self.signature = signature_data
        self.arg_address = arg_address
        self.base_address = base_address
        self.args_array_size = args_array_size
    
    def calculate_addresses(self):
        """Calculate memory addresses for arguments and return value."""
        addresses = {
            'arguments': [],
            'return': {}
        }
        
        for idx, param in enumerate(self.signature['parameters']):
            addr = self.arg_address + (idx * 4)
            addresses['arguments'].append({
                'index': idx,
                'name': param['name'],
                'type': param['type'],
                'category': param['category'],
                'address': f"0x{addr:08x}"
            })
        
        return_idx = self.args_array_size - 1
        return_addr = self.arg_address + (return_idx * 4)
        addresses['return'] = {
            'type': self.signature['return_type'],
            'index': return_idx,
            'address': f"0x{return_addr:08x}"
        }
        
        return addresses
    
    def generate_metadata(self):
        """Generate complete metadata dictionary."""
        addresses = self.calculate_addresses()
        
        metadata = {
            'function': {
                'name': self.signature['name'],
                'return_type': self.signature['return_type'],
                'wrapper_entry': 'call_remote'
            },
            'addresses': {
                'code_base': f"0x{self.base_address:08x}",
                'arg_base': f"0x{self.arg_address:08x}",
                'args_array_size': self.args_array_size,
                'args_array_bytes': self.args_array_size * 4
            },
            'arguments': addresses['arguments'],
            'result': addresses['return']
        }
        
        return metadata
    
    def save_json(self, output_dir):
        """
        Save metadata as JSON file in output directory.
        
        Args:
            output_dir: Directory to save signature.json
            
        Returns:
            str: Path to generated signature.json file
        """
        os.makedirs(output_dir, exist_ok=True)
        
        metadata = self.generate_metadata()
        
        output_path = os.path.join(output_dir, 'signature.json')
        
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return output_path
