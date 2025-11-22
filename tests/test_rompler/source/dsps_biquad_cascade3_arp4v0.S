// Author: Boumedine Billal
// https://github.com/BoumedineBillal
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0

// ============================================================================
// BASELINE CASCADED BIQUAD IMPLEMENTATION (V0)
// ============================================================================
// This is the initial fused implementation of 3 cascaded biquad filters.
// 
// OPTIMIZATION OVER 3 SEPARATE CALLS:
// - Eliminates 2N memory loads and 2N memory stores by keeping intermediate
//   results in registers between stages
// - Original: Load → Stage1 → Store → Load → Stage2 → Store → Load → Stage3 → Store
// - Fused:    Load → Stage1 → Stage2 → Stage3 → Store
// 
// CHARACTERISTICS:
// - Stack frame: 48 bytes (stores fs0-fs5)
// - Sequential instruction ordering following the mathematical formula
// - Each stage computes: d0 = x - a1*w0 - a2*w1
//                        y  = b0*d0 + b1*w0 + b2*w1
// - Simple, readable implementation prioritizing correctness
//
// PERFORMANCE: ~30-33 cycles per sample through all 3 stages
// ============================================================================

    .text
    .align  4
    .global dsps_biquad_f32_cascade3_arp4v0
    .type   dsps_biquad_f32_cascade3_arp4v0,@function

// Fused 3-cascade biquad filter for ESP32-P4
// void dsps_biquad_f32_cascade3_arp4v0(float* inout, int len, float* coef, 
//                                       float* w1, float* w2, float* w3)
// a0 - inout buffer pointer
// a1 - length
// a2 - coefficients pointer (shared for all 3 stages)
// a3 - w1 state pointer
// a4 - w2 state pointer  
// a5 - w3 state pointer

dsps_biquad_f32_cascade3_arp4v0:
    addi    sp, sp, -48
    fsw     fs0, 0(sp)
    fsw     fs1, 4(sp)
    fsw     fs2, 8(sp)
    fsw     fs3, 12(sp)
    fsw     fs4, 16(sp)
    fsw     fs5, 20(sp)
    
    // Load shared coefficients
    flw     fa0, 0(a2)      // b0
    flw     fa1, 4(a2)      // b1
    flw     fa2, 8(a2)      // b2
    flw     fa3, 12(a2)     // a1
    flw     fa4, 16(a2)     // a2
    fneg.s  fa3, fa3        // -a1
    fneg.s  fa4, fa4        // -a2
    
    // Load state for stage 1
    flw     fs0, 0(a3)      // w1_0
    flw     fs1, 4(a3)      // w1_1
    
    // Load state for stage 2
    flw     fs2, 0(a4)      // w2_0
    flw     fs3, 4(a4)      // w2_1
    
    // Load state for stage 3
    flw     fs4, 0(a5)      // w3_0
    flw     fs5, 4(a5)      // w3_1

    esp.lp.setup 0, a1, .cascade3_loop_end
        flw     ft0, 0(a0)          // Load input sample
        
        // Stage 1 - Sequential computation
        fmadd.s ft0, fs0, fa3, ft0  // d0 = x - a1*w0
        fmul.s  ft1, fa1, fs0       // temp = b1*w0
        fmadd.s ft0, fs1, fa4, ft0  // d0 -= a2*w1
        fmadd.s ft1, ft0, fa0, ft1  // temp += b0*d0
        fmadd.s ft1, fa2, fs1, ft1  // y1 = temp + b2*w1
        fmv.s   fs1, fs0            // w1_1 = w1_0
        fmv.s   fs0, ft0            // w1_0 = d0
        
        // Stage 2 (input = ft1)
        fmadd.s ft1, fs2, fa3, ft1  // d0 = y1 - a1*w0
        fmul.s  ft2, fa1, fs2       // temp = b1*w0
        fmadd.s ft1, fs3, fa4, ft1  // d0 -= a2*w1
        fmadd.s ft2, ft1, fa0, ft2  // temp += b0*d0
        fmadd.s ft2, fa2, fs3, ft2  // y2 = temp + b2*w1
        fmv.s   fs3, fs2            // w2_1 = w2_0
        fmv.s   fs2, ft1            // w2_0 = d0
        
        // Stage 3 (input = ft2)
        fmadd.s ft2, fs4, fa3, ft2  // d0 = y2 - a1*w0
        fmul.s  ft3, fa1, fs4       // temp = b1*w0
        fmadd.s ft2, fs5, fa4, ft2  // d0 -= a2*w1
        fmadd.s ft3, ft2, fa0, ft3  // temp += b0*d0
        fmadd.s ft3, fa2, fs5, ft3  // y3 = temp + b2*w1
        fmv.s   fs5, fs4            // w3_1 = w3_0
        fmv.s   fs4, ft2            // w3_0 = d0
        
        fsw     ft3, 0(a0)          // Store final output
        addi    a0, a0, 4
.cascade3_loop_end: nop
    
    // Store back state variables
    fsw     fs0, 0(a3)
    fsw     fs1, 4(a3)
    fsw     fs2, 0(a4)
    fsw     fs3, 4(a4)
    fsw     fs4, 0(a5)
    fsw     fs5, 4(a5)
    
    // Restore saved registers
    flw     fs0, 0(sp)
    flw     fs1, 4(sp)
    flw     fs2, 8(sp)
    flw     fs3, 12(sp)
    flw     fs4, 16(sp)
    flw     fs5, 20(sp)
    addi    sp, sp, 48
    
    ret