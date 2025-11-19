// vector.S - Assembly implementation with preprocessor directives

    .section .text
    .global asm_square
    .type asm_square, @function

// Simple assembly function: square a number
// int32_t asm_square(int32_t x);
// Input: a0 = x
// Output: a0 = x * x
asm_square:
    mul     a0, a0, a0      // a0 = a0 * a0
    ret

    .size asm_square, .-asm_square
