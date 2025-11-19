import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from esp32_loader import Builder


def main():
    print("ESP32-P4 Dynamic Code Loader - Multi-Function Example")
    print("=" * 60)
    
    builder = Builder()
    
    source_path = os.path.join(os.path.dirname(__file__), 'sources', 'compute.c')
    
    # Build with optimization level O3
    print(f"\nBuilding: {source_path}")
    print(f"Optimization: O3")
    print(f"Entry point: compute")
    print(f"Base address: 0x40800000")
    
    binary = builder.build(
        source=source_path,
        entry_point='compute',
        base_address=0x40800000,
        optimization='O3'
    )
    
    print(f"\n✓ Build successful!")
    
    # Show all available functions
    print("\nAvailable Functions:")
    print("-" * 60)
    for func in binary.functions:
        print(f"  {func['name']:25s}  0x{func['address']:08x}  ({func['size']:3d} bytes)")
    
    # Generate C header file with addresses
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    header_path = os.path.join(output_dir, 'function_addresses.h')
    with open(header_path, 'w') as f:
        f.write("// Auto-generated function addresses\n")
        f.write(f"// Generated from: {os.path.basename(source_path)}\n")
        f.write(f"// Base address: 0x{binary.base_address:08x}\n\n")
        f.write("#ifndef FUNCTION_ADDRESSES_H\n")
        f.write("#define FUNCTION_ADDRESSES_H\n\n")
        
        for func in binary.functions:
            name_upper = func['name'].upper()
            f.write(f"#define {name_upper}_ADDR  0x{func['address']:08x}\n")
        
        f.write("\n// Function pointer typedefs\n")
        f.write("typedef int32_t (*compute_func_t)(int32_t, int32_t);\n")
        f.write("typedef uint32_t (*get_count_func_t)(void);\n")
        f.write("typedef int32_t (*get_sum_func_t)(void);\n")
        
        f.write("\n#endif // FUNCTION_ADDRESSES_H\n")
    
    print(f"\n✓ Generated C header: {header_path}")
    
    # Save binary and metadata
    binary.save_bin(os.path.join(output_dir, 'compute_o3.bin'))
    binary.save_metadata(os.path.join(output_dir, 'metadata_o3.json'))
    
    # Show comparison with different optimization
    print("\nCompiling with O0 for comparison...")
    binary_o0 = builder.build(
        source=source_path,
        entry_point='compute',
        base_address=0x40800000,
        optimization='O0'
    )
    
    print(f"\nOptimization Comparison:")
    print(f"  O0: {binary_o0.total_size} bytes")
    print(f"  O3: {binary.total_size} bytes")
    print(f"  Reduction: {binary_o0.total_size - binary.total_size} bytes ({(1 - binary.total_size/binary_o0.total_size)*100:.1f}%)")
    
    # Show metadata
    print("\nMetadata Preview:")
    metadata = binary.get_metadata_dict()
    print(f"  Entry: {metadata['entry_point']} @ {metadata['entry_address']}")
    print(f"  Total: {metadata['total_size']} bytes")
    print(f"  Sections: {len(metadata['sections'])}")
    print(f"  Functions: {len(metadata['functions'])}")
    
    print("\n" + "=" * 60)
    print("Build complete!")
    print(f"\nFiles created by this example:")
    created_files = [
        'function_addresses.h',
        'compute_o3.bin',
        'metadata_o3.json'
    ]
    for fname in created_files:
        fpath = os.path.join(output_dir, fname)
        if os.path.exists(fpath):
            size = os.path.getsize(fpath)
            print(f"  - {fname:30s} ({size:6d} bytes)")


if __name__ == '__main__':
    main()
