    .text
    .align 4
    .global vector_scale_asm
    .type vector_scale_asm, @function

// Optimized vector scaling: out[i] = in[i] * scale
// void vector_scale_asm(float* in, float* out, int len, float scale)
// a0 = in, a1 = out, a2 = len, fa0 = scale

vector_scale_asm:
    beqz    a2, .done          // if len == 0, exit
    
.loop:
    flw     ft0, 0(a0)         // Load input
    fmul.s  ft0, ft0, fa0      // Multiply by scale
    fsw     ft0, 0(a1)         // Store output
    
    addi    a0, a0, 4          // in++
    addi    a1, a1, 4          // out++
    addi    a2, a2, -1         // len--
    bnez    a2, .loop          // Continue if len > 0
    
.done:
    ret
