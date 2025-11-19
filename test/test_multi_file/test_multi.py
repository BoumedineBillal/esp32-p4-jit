import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from esp32_loader import Builder


def main():
    print("=" * 70)
    print("ESP32-P4 Multi-File Compilation Test")
    print("=" * 70)
    
    builder = Builder()
    
    # Source path points to main entry file
    source_path = os.path.join(os.path.dirname(__file__), 'sources', 'main.c')
    
    print(f"\nEntry file: {os.path.basename(source_path)}")
    print(f"Entry point: main")
    print(f"Base address: 0x40800000")
    print()
    
    try:
        binary = builder.build(
            source=source_path,
            entry_point='main',
            base_address=0x40800000
        )
        
        print(f"\n{'=' * 70}")
        print(f"✓ Build successful!")
        print(f"{'=' * 70}")
        print(f"  Entry point: 0x{binary.entry_address:08x}")
        print(f"  Total size: {binary.total_size} bytes")
        print()
        
        # Show sections
        binary.print_sections()
        print()
        
        # Show all functions
        binary.print_symbols()
        print()
        
        # Show memory map
        binary.print_memory_map()
        
        # Save outputs in test folder
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        binary.save_bin(os.path.join(output_dir, 'multi.bin'))
        binary.save_elf(os.path.join(output_dir, 'multi.elf'))
        binary.save_metadata(os.path.join(output_dir, 'metadata.json'))
        
        print(f"\n{'=' * 70}")
        print(f"Outputs saved to: {output_dir}/")
        print(f"  - multi.bin ({binary.total_size} bytes)")
        print(f"  - multi.elf")
        print(f"  - metadata.json")
        print(f"{'=' * 70}")
        
        binary.disassemble()
        
    except Exception as e:
        print(f"\n{'=' * 70}")
        print(f"✗ Build failed!")
        print(f"{'=' * 70}")
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    main()
