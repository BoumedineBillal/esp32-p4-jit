import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from esp32_loader import Builder



print("ESP32-P4 Dynamic Code Loader - Simple Example")
print("=" * 60)

builder = Builder()

source_path = os.path.join(os.path.dirname(__file__), 'sources', 'compute.c')

print(f"\nBuilding: {source_path}")
print(f"Entry point: compute")
print(f"Base address: 0x40800000")

binary = builder.build(
    source=source_path,
    entry_point='InterpolateWaveHermite',
    base_address=0x40800000
)

print(f"\n✓ Build successful!")
print(f"  Entry point: 0x{binary.entry_address:08x}")
print(f"  Total size: {binary.total_size} bytes")

print()
binary.print_sections()

print()
binary.print_symbols()

print()
binary.print_memory_map()

output_dir = os.path.join(os.path.dirname(__file__), 'output')
os.makedirs(output_dir, exist_ok=True)

print(f"\nSaving outputs to: {output_dir}")
binary.save_bin(os.path.join(output_dir, 'compute.bin'))
binary.save_elf(os.path.join(output_dir, 'compute.elf'))
binary.save_metadata(os.path.join(output_dir, 'metadata.json'))

print("\nFiles saved:")
print(f"  - compute.bin ({binary.total_size} bytes)")
print(f"  - compute.elf")
print(f"  - metadata.json")

print("\nRaw binary data (first 64 bytes):")
data = binary.get_data()
for i in range(0, min(64, len(data)), 16):
    hex_str = ' '.join(f'{b:02x}' for b in data[i:i+16])
    print(f"  {i:04x}: {hex_str}")

print("\n" + "=" * 60)
print("Build complete! Binary ready for loading to ESP32-P4.")

binary.disassemble()
