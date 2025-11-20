import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from esp32_loader import Builder


def main():
    print("=" * 70)
    print("ESP32-P4 Wrapper Generation Test")
    print("=" * 70)
    print()
    
    builder = Builder()
    
    source_path = os.path.join(os.path.dirname(__file__), 'sources', 'test_func.c')
    
    print("Building with automatic wrapper generation:")
    print(f"  Source: {os.path.basename(source_path)}")
    print(f"  Function: compute2")
    print(f"  Code base: 0x40800000")
    print(f"  Args base: 0x50000000")
    print()
    print("=" * 70)
    print()
    
    try:
        # Use wrapper builder
        binary = builder.wrapper.build_with_wrapper(
            source=source_path,
            function_name='InterpolateWaveHermite', # InterpolateWaveHermite compute2 
            base_address=0x40800000,
            arg_address=0x50000000,
            output_dir=os.path.join(os.path.dirname(__file__), 'output')
        )
        
        print()
        print("=" * 70)
        print("✓ Wrapper build successful!")
        print("=" * 70)
        print(f"  Entry point: 0x{binary.entry_address:08x}")
        print(f"  Total size: {binary.total_size} bytes")
        print()
        
        # Show sections
        binary.print_sections()
        print()
        
        # Show functions
        binary.print_symbols()
        print()
        
        # Save outputs
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        binary.save_bin(os.path.join(output_dir, 'wrapped.bin'))
        binary.save_elf(os.path.join(output_dir, 'wrapped.elf'))
        binary.save_metadata(os.path.join(output_dir, 'metadata.json'))
        
        print()
        print("=" * 70)
        print("Files generated:")
        print("=" * 70)
        
        # List generated files
        source_dir = os.path.dirname(source_path)
        temp_c = os.path.join(source_dir, 'temp.c')
        if os.path.exists(temp_c):
            print(f"  Source: {temp_c}")
        
        files = [
            ('wrapped.bin', 'Binary file'),
            ('wrapped.elf', 'ELF file'),
            ('metadata.json', 'Build metadata'),
            ('signature.json', 'Function signature')
        ]
        
        for fname, desc in files:
            fpath = os.path.join(output_dir, fname)
            if os.path.exists(fpath):
                size = os.path.getsize(fpath)
                print(f"  Output: {fname:20s} ({size:6d} bytes) - {desc}")
        
        print()
        print("=" * 70)
        print("Test completed successfully!")
        print("=" * 70)
        
        binary.disassemble()
        
    except Exception as e:
        print()
        print("=" * 70)
        print("✗ Build failed!")
        print("=" * 70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
