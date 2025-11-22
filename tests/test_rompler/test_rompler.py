import os
import sys
import struct
import math
import numpy as np
import matplotlib.pyplot as plt
import time
import pandas as pd

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from esp32_loader import Builder
from p4_jit import JITSession
from p4_jit.memory_caps import MALLOC_CAP_SPIRAM, MALLOC_CAP_8BIT, MALLOC_CAP_INTERNAL

# ==========================================
# PYTHON REFERENCE IMPLEMENTATION
# ==========================================

def python_biquad_gen_lpf(f, qFactor):
    if qFactor <= 0.0001:
        qFactor = 0.0001
    Fs = 1.0
    w0 = 2.0 * np.pi * f / Fs
    c = np.cos(w0)
    s = np.sin(w0)
    alpha = s / (2.0 * qFactor)

    b0 = (1.0 - c) / 2.0
    b1 = 1.0 - c
    b2 = b0
    a0 = 1.0 + alpha
    a1 = -2.0 * c
    a2 = 1.0 - alpha

    return np.array([b0/a0, b1/a0, b2/a0, a1/a0, a2/a0], dtype=np.float32)

def python_biquad_process(input_data, coeffs, w):
    output = np.zeros_like(input_data)
    for i in range(len(input_data)):
        d0 = input_data[i] - coeffs[3] * w[0] - coeffs[4] * w[1]
        output[i] = coeffs[0] * d0 + coeffs[1] * w[0] + coeffs[2] * w[1]
        w[1] = w[0]
        w[0] = d0
    return output

def python_rompler_process(large_audio_buffer, total_samples, phase_increment):
    # Simulate the exact logic of the C code
    read_buffer_phase = 0.0
    output_block_size = 32
    current_read_pos = 4
    
    # State variables
    coeffs_lpf = np.zeros(5, dtype=np.float32)
    w_lpf1 = np.zeros(2, dtype=np.float32)
    w_lpf2 = np.zeros(2, dtype=np.float32)
    w_lpf3 = np.zeros(2, dtype=np.float32)
    
    # Make a copy to work on
    buffer_copy = large_audio_buffer.copy()
    
    STOPPED = 0
    READFIRST = 1
    READLAST = 2
    RUNNING = 3
    
    current_status = READFIRST
    
    while current_read_pos < total_samples:
        read_buffer_length = int(phase_increment * output_block_size + read_buffer_phase)
        total_phase = phase_increment * output_block_size + read_buffer_phase
        read_buffer_phase = total_phase - float(read_buffer_length)
        
        if current_read_pos + read_buffer_length > total_samples:
            read_buffer_length = total_samples - current_read_pos
            
        if read_buffer_length == 0:
            break
            
        if current_status == READFIRST:
            base = current_read_pos - 4
            buffer_copy[base + 0] = 0.001 * buffer_copy[base + 4]
            buffer_copy[base + 1] = 0.01  * buffer_copy[base + 4]
            buffer_copy[base + 2] = 0.1   * buffer_copy[base + 4]
            buffer_copy[base + 3] = 0.5   * buffer_copy[base + 4]
            
        f_anti_alias = 0.5 / phase_increment
        if f_anti_alias < 0.5:
            coeffs_lpf = python_biquad_gen_lpf(f_anti_alias, 0.5)
            chunk = buffer_copy[current_read_pos : current_read_pos + read_buffer_length]
            chunk = python_biquad_process(chunk, coeffs_lpf, w_lpf1)
            chunk = python_biquad_process(chunk, coeffs_lpf, w_lpf2)
            chunk = python_biquad_process(chunk, coeffs_lpf, w_lpf3)
            buffer_copy[current_read_pos : current_read_pos + read_buffer_length] = chunk

        current_read_pos += read_buffer_length
        
        if current_status == READFIRST:
            current_status = RUNNING
            
    return buffer_copy

# ==========================================
# TEST RUNNER
# ==========================================

def run_test_suite(session, builder, function_name, label):
    print(f"\n{'='*60}")
    print(f"TESTING: {label} ({function_name})")
    print(f"{'='*60}")
    
    source_file = os.path.join(os.path.dirname(__file__), 'source', 'rompler.c')
    
    # 1. Build (Pass 1)
    print("Building (Pass 1)...")
    try:
        temp_bin = builder.wrapper.build_with_wrapper(
            source=source_file, 
            function_name=function_name,
            base_address=0x03000004,
            arg_address=0x00030004,
            use_firmware_elf=True 
        )
    except RuntimeError as e:
        print(f"Build failed: {e}")
        return None

    # 2. Allocate
    CAP_EXEC = MALLOC_CAP_INTERNAL 
    CAP_DATA = MALLOC_CAP_INTERNAL # User requested SRAM for data
    
    padding = 64
    alloc_size = temp_bin.total_size + padding
    print(f"Allocating {alloc_size} bytes for code...")
    code_addr = session.device.allocate(alloc_size, CAP_EXEC, 128)
    args_addr = session.device.allocate(128, CAP_DATA, 128)
    
    # 3. Build (Pass 2)
    print("Building (Pass 2)...")
    final_bin = builder.wrapper.build_with_wrapper(
        source=source_file, 
        function_name=function_name,
        base_address=code_addr, 
        arg_address=args_addr,
        use_firmware_elf=True
    )
    
    # 4. Load
    print("Loading function...")
    remote_func = session.load_function(final_bin, args_addr)
    
    # 5. Prepare Data
    SAMPLE_RATE = 48000
    DURATION_SEC = 0.05
    TOTAL_SAMPLES = int(SAMPLE_RATE * DURATION_SEC)
    PADDING = 4
    BUFFER_SIZE = TOTAL_SAMPLES + PADDING
    
    t = np.linspace(0, DURATION_SEC, TOTAL_SAMPLES)
    f0, f1 = 100, 5000
    k = (f1 - f0) / DURATION_SEC
    input_signal = np.sin(2 * np.pi * (f0 * t + 0.5 * k * t**2)).astype(np.float32)
    
    full_buffer_ref = np.zeros(BUFFER_SIZE, dtype=np.float32)
    full_buffer_ref[PADDING:] = input_signal
    
    # Allocate Buffers
    audio_buf_addr = session.device.allocate(BUFFER_SIZE * 4, CAP_DATA, 16)
    coeffs_addr = session.device.allocate(5 * 4, CAP_DATA, 16)
    w1_addr = session.device.allocate(2 * 4, CAP_DATA, 16)
    w2_addr = session.device.allocate(2 * 4, CAP_DATA, 16)
    w3_addr = session.device.allocate(2 * 4, CAP_DATA, 16)
    
    test_cases = [
        {"name": "No Pitch Shift", "phase_inc": 1.0},
        {"name": "Pitch Up (LPF)", "phase_inc": 2.0},
        {"name": "Pitch Down", "phase_inc": 0.5},
        {"name": "Extreme Pitch", "phase_inc": 4.0},
    ]
    
    results = []
    
    for case in test_cases:
        print(f"  Running: {case['name']} (Inc={case['phase_inc']})...", end='')
        
        # Reset Memory
        session.device.write_memory(audio_buf_addr, full_buffer_ref.tobytes())
        session.device.write_memory(coeffs_addr, b'\x00' * 20)
        session.device.write_memory(w1_addr, b'\x00' * 8)
        session.device.write_memory(w2_addr, b'\x00' * 8)
        session.device.write_memory(w3_addr, b'\x00' * 8)
        
        # Execute
        args = struct.pack("<IIfIIII", 
                           audio_buf_addr, BUFFER_SIZE, case['phase_inc'], 
                           coeffs_addr, w1_addr, w2_addr, w3_addr)
        
        start_time = time.time()
        remote_func(args)
        host_time_ms = (time.time() - start_time) * 1000
        
        # Read Cycles
        cycles_bytes = session.device.read_memory(args_addr + 124, 4)
        cycles = struct.unpack("<I", cycles_bytes)[0]
        p4_exec_us = cycles / 360.0
        
        # Read Result
        res_bytes = session.device.read_memory(audio_buf_addr, BUFFER_SIZE * 4)
        p4_output = np.frombuffer(res_bytes, dtype=np.float32)[PADDING:]
        
        # Python Ref
        py_full_out = python_rompler_process(full_buffer_ref, BUFFER_SIZE, case['phase_inc'])
        py_output = py_full_out[PADDING:]
        
        # Compare
        diff = np.abs(p4_output - py_output)
        max_err = np.max(diff)
        mse = np.mean(diff**2)
        
        print(f" Done. Time: {p4_exec_us:.2f} us, MaxErr: {max_err:.6f}")
        
        results.append({
            "case": case['name'],
            "phase_inc": case['phase_inc'],
            "p4_out": p4_output,
            "py_out": py_output,
            "diff": diff,
            "max_err": max_err,
            "mse": mse,
            "cycles": cycles,
            "exec_us": p4_exec_us,
            "host_ms": host_time_ms
        })
        
    # Cleanup
    session.device.free(code_addr)
    session.device.free(args_addr)
    session.device.free(audio_buf_addr)
    session.device.free(coeffs_addr)
    session.device.free(w1_addr)
    session.device.free(w2_addr)
    session.device.free(w3_addr)
    
    return {
        "label": label,
        "binary_size": final_bin.total_size,
        "results": results,
        "binary": final_bin
    }

def generate_plots(suite_results):
    for suite in suite_results:
        label = suite['label']
        results = suite['results']
        
        print(f"Generating plots for {label}...")
        fig, axes = plt.subplots(len(results), 3, figsize=(15, 4 * len(results)))
        fig.suptitle(f"{label} vs Python Reference", fontsize=16)
        
        for i, res in enumerate(results):
            t = np.linspace(0, 0.05, len(res['p4_out']))
            
            # Plot 1: Signals
            ax1 = axes[i, 0]
            ax1.plot(t, res['py_out'], 'k-', linewidth=2, label='Ref', alpha=0.5)
            ax1.plot(t, res['p4_out'], 'r--', linewidth=1.5, label='JIT')
            ax1.set_title(f"{res['case']} (Inc={res['phase_inc']})")
            ax1.legend()
            ax1.grid(True)
            
            # Plot 2: Error
            ax2 = axes[i, 1]
            ax2.plot(t, res['diff'], 'b-')
            ax2.set_title(f"Error (Max: {res['max_err']:.6f})")
            ax2.grid(True)
            
            # Plot 3: Spectrogram
            ax3 = axes[i, 2]
            ax3.specgram(res['p4_out'], Fs=48000, NFFT=256, noverlap=128)
            ax3.set_title("Spectrogram")
            
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        safe_label = label.replace(" ", "_")
        plt.savefig(os.path.join(os.path.dirname(__file__), f"rompler_{safe_label}.png"))

def generate_table_plot(df):
    # Create a figure to plot the table
    fig, ax = plt.subplots(figsize=(12, 10)) 
    ax.axis('off')
    ax.axis('tight')
    
    # Round float values for display
    display_df = df.copy()
    # Format all numeric values
    for col in display_df.columns:
        for idx in display_df.index:
            val = display_df.loc[idx, col]
            if isinstance(val, (float, np.floating)):
                if "(%)" in str(idx):
                    display_df.loc[idx, col] = f"{val:.2f}%"
                else:
                    display_df.loc[idx, col] = f"{val:.2f}"
        
    # Create table with row labels
    table = ax.table(cellText=display_df.values, colLabels=display_df.columns, rowLabels=display_df.index, cellLoc='center', loc='center')
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5)
    
    # Add colors
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor('#40466e')
        elif row % 2 == 0:
            cell.set_facecolor('#f5f5f5')
            
    plt.title("Rompler Performance Comparison (C vs ASM)\nData and Binary in Internal SRAM", fontsize=16, weight='bold', pad=20)
    plt.tight_layout()
    
    plot_path = os.path.join(os.path.dirname(__file__), "rompler_performance_table.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"Performance table saved to: {plot_path}")

def test_rompler_comparison():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    builder = Builder()
    
    session = JITSession()
    try:
        session.connect()
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # Run Tests
    suites = []
    
    # 1. C Implementation
    res_c = run_test_suite(session, builder, "Rompler_ApplyToLargeBuffer", "C Implementation")
    if res_c: suites.append(res_c)
    
    # 2. ASM Implementation (Fused)
    res_asm = run_test_suite(session, builder, "Rompler_ApplyToLargeBuffer2", "ASM Implementation")
    if res_asm: suites.append(res_asm)

    # 3. ASM (Single Biquad) Implementation
    res_asm_single = run_test_suite(session, builder, "Rompler_ApplyToLargeBuffer3", "ASM (Single Biquad)")
    if res_asm_single: suites.append(res_asm_single)
    
    # Generate Plots
    generate_plots(suites)
    
    # Generate Comparison Table
    print("\n" + "="*80)
    print("PERFORMANCE COMPARISON SUMMARY")
    print("="*80)
    
    # Flatten results
    data = []
    for suite in suites:
        label = suite['label']
        bin_size = suite['binary_size']
        for res in suite['results']:
            data.append({
                "Implementation": label,
                "Test Case": res['case'],
                "Phase Inc": res['phase_inc'],
                "Time (us)": res['exec_us'],
                "Cycles": res['cycles'],
                "Max Error": res['max_err'],
                "Binary Size": bin_size
            })
            
    if not data:
        print("No results to process.")
        return

    # Separate results
    results_c = [d for d in data if d['Implementation'] == "C Implementation"]
    results_asm = [d for d in data if d['Implementation'] == "ASM Implementation"]
    results_asm_single = [d for d in data if d['Implementation'] == "ASM (Single Biquad)"]
    
    if results_c and results_asm and results_asm_single:
        df_c = pd.DataFrame(results_c).set_index('Test Case')
        df_asm = pd.DataFrame(results_asm).set_index('Test Case')
        df_asm_single = pd.DataFrame(results_asm_single).set_index('Test Case')
        
        # Build Summary DataFrame
        summary = pd.DataFrame()
        summary['Phase Inc'] = df_c['Phase Inc']
        summary['C Time (us)'] = df_c['Time (us)']
        summary['ASM (Fused) Time (us)'] = df_asm['Time (us)']
        summary['ASM (Single) Time (us)'] = df_asm_single['Time (us)']
        
        # Calculate Improvement % (Fused vs Single)
        summary['Fused vs Single (%)'] = ((summary['ASM (Single) Time (us)'] - summary['ASM (Fused) Time (us)']) / summary['ASM (Single) Time (us)'] * 100)
        
        summary['C Cycles'] = df_c['Cycles']
        summary['ASM (Fused) Cycles'] = df_asm['Cycles']
        summary['ASM (Single) Cycles'] = df_asm_single['Cycles']
        
        summary['C Size (B)'] = df_c['Binary Size']
        summary['ASM (Fused) Size (B)'] = df_asm['Binary Size']
        summary['ASM (Single) Size (B)'] = df_asm_single['Binary Size']
        
        summary['Max Error'] = df_asm['Max Error'] # Assuming similar error profile
        
        # Transpose for vertical table
        summary_T = summary.T
        
        print(summary_T.to_string())
        generate_table_plot(summary_T)
        
    else:
        print("Could not compare all implementations (missing data).")
        df = pd.DataFrame(data)
        print(df.to_string())
        
    # Disassemble the ASM binaries for inspection
    if res_asm:
        print("\nDisassembling ASM (Fused) binary...")
        res_asm['binary'].disassemble("asm_fused.txt", False)
        res_asm['binary'].print_memory_map()
        
    if res_asm_single:
        print("\nDisassembling ASM (Single) binary...")
        res_asm_single['binary'].disassemble("asm_single.txt", False)
        res_asm_single['binary'].print_memory_map()

if __name__ == "__main__":
    test_rompler_comparison()
