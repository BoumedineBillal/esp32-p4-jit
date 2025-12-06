#include <stdint.h>
#include <stdio.h>

// Read RISC-V cycle counter
static inline uint32_t rdcycle(void) {
    uint32_t cycles;
    asm volatile ("rdcycle %0" : "=r"(cycles));
    return cycles;
}

static inline int32_t relu_int32(int32_t x) { return (x > 0) ? x : 0; }
static inline int8_t clip_int8(int32_t x) {
    return (x > 127) ? 127 : ((x < -128) ? -128 : (int8_t)x);
}

// Conv2d with ReLU BEFORE quantization
void conv2d_int8(
    const int8_t* input, int in_h, int in_w, int in_c,
    const int8_t* weight, const int8_t* bias,
    int8_t* output, int out_c,
    int exp_in, int exp_w, int exp_out
) {
    const int K = 3, P = 1, S = 1;
    int out_h = (in_h + 2*P - K) / S + 1;
    int out_w = (in_w + 2*P - K) / S + 1;
    
    int acc_shift = exp_in + exp_w - exp_out;
    
    for (int oc = 0; oc < out_c; oc++) {
        for (int oh = 0; oh < out_h; oh++) {
            for (int ow = 0; ow < out_w; ow++) {
                int32_t acc = 0;
                
                // MAC
                for (int ic = 0; ic < in_c; ic++) {
                    for (int kh = 0; kh < K; kh++) {
                        for (int kw = 0; kw < K; kw++) {
                            int ih = oh * S - P + kh;
                            int iw = ow * S - P + kw;
                            
                            if (ih >= 0 && ih < in_h && iw >= 0 && iw < in_w) {
                                acc += (int32_t)input[(ic * in_h + ih) * in_w + iw] *
                                       (int32_t)weight[((oc * in_c + ic) * K + kh) * K + kw];
                            }
                        }
                    }
                }
                
                // Add bias (scaled by E_in)
                acc += (int32_t)bias[oc] << exp_in;
                
                // ReLU BEFORE quantization
                acc = relu_int32(acc);
                
                // Scale to output
                acc = acc >> acc_shift;
                
                output[(oc * out_h + oh) * out_w + ow] = clip_int8(acc);
            }
        }
    }
}

void maxpool2d_int8(const int8_t* input, int8_t* output, int h, int w, int c) {
    int out_h = h / 2, out_w = w / 2;
    for (int ch = 0; ch < c; ch++) {
        for (int oh = 0; oh < out_h; oh++) {
            for (int ow = 0; ow < out_w; ow++) {
                int8_t max_val = -128;
                for (int kh = 0; kh < 2; kh++) {
                    for (int kw = 0; kw < 2; kw++) {
                        int8_t v = input[(ch * h + oh*2 + kh) * w + ow*2 + kw];
                        if (v > max_val) max_val = v;
                    }
                }
                output[(ch * out_h + oh) * out_w + ow] = max_val;
            }
        }
    }
}

// FC layer with ReLU BEFORE quantization
void fc_int8(
    const int8_t* input, int in_size,
    const int8_t* weight, const int8_t* bias,
    int8_t* output, int out_size,
    int exp_in, int exp_w, int exp_out
) {
    int acc_shift = exp_in + exp_w - exp_out;
    
    for (int i = 0; i < out_size; i++) {
        int32_t acc = 0;
        for (int j = 0; j < in_size; j++) {
            acc += (int32_t)input[j] * (int32_t)weight[i * in_size + j];
        }
        
        // Add bias (scaled by E_in)
        acc += (int32_t)bias[i] << exp_in;
        
        // ReLU BEFORE quantization
        acc = relu_int32(acc);
        
        // Scale to output
        acc = acc >> acc_shift;
        
        output[i] = clip_int8(acc);
    }
}

// FC layer WITHOUT quantization (for final layer)
void fc_int32(
    const int8_t* input, int in_size,
    const int8_t* weight, const int8_t* bias,
    int32_t* output, int out_size,
    int exp_in, int exp_w
) {
    for (int i = 0; i < out_size; i++) {
        int32_t acc = 0;
        for (int j = 0; j < in_size; j++) {
            acc += (int32_t)input[j] * (int32_t)weight[i * in_size + j];
        }
        
        // Add bias (scaled by E_in)
        acc += (int32_t)bias[i] << exp_in;
        
        // NO ReLU, NO quantization - raw logits
        output[i] = acc;
    }
}

void fc_int32_p4simd(
    const int8_t* input, int in_size,
    const int8_t* weight, const int8_t* bias,
    int32_t* output, int out_size,
    int exp_in, int exp_w
) {
    // Current pointer to weights (increments monotonically)
    const int8_t* w_ptr = weight;
    
    // Calculate loop iterations (16 bytes per iteration)
    int loop_count = in_size >> 4; 

    for (int i = 0; i < out_size; i++) {
        // CRITICAL FIX: ESP32-P4 PIE instructions are restricted to the 
        // a0-a5 (x10-x15) register range. We must force variables into these registers.
        
        register const int8_t* in_ptr asm("a0") = input;
        register const int8_t* cur_w_ptr asm("a1") = w_ptr;
        register int32_t acc_val asm("a2");
        register int cnt asm("a3") = loop_count;
        register int shift_reg asm("a4") = 0;

        asm volatile (
            "esp.zero.xacc \n\t"                   // Clear accumulator
            "esp.lp.setup 0, %[cnt], 1f \n\t"      // Setup HW loop 0
            "0: \n\t"                              // Loop start label
            "esp.vld.128.ip q0, %[in], 16 \n\t"    // Load 16 inputs (uses a0)
            "esp.vld.128.ip q1, %[w], 16 \n\t"     // Load 16 weights (uses a1)
            "esp.vmulas.s8.xacc q0, q1 \n\t"       // Multiply & Accumulate
            "1: \n\t"                              // Loop end label
            "esp.srs.s.xacc %[res], %[shft] \n\t"  // Extract result (uses a2, a4)

            // Output Operands
            : [res] "=r" (acc_val),       // Mapped to a2
              [in]  "+r" (in_ptr),        // Mapped to a0
              [w]   "+r" (cur_w_ptr)      // Mapped to a1
            
            // Input Operands
            : [cnt] "r" (cnt),            // Mapped to a3
              [shft] "r" (shift_reg)      // Mapped to a4
            
            // Clobbers
            : "memory"
        );

        w_ptr = cur_w_ptr; 
        output[i] = acc_val + ((int32_t)bias[i] << exp_in);
    }
}

// Inference function WITH TIMING
int32_t mnist_inference(
    int8_t* input,
    int8_t* w_conv1, int8_t* b_conv1,
    int8_t* w_conv2, int8_t* b_conv2,
    int8_t* w_fc1, int8_t* b_fc1,
    int8_t* w_fc2, int8_t* b_fc2,
    int32_t e_in,
    int32_t e_conv1_w, int32_t e_conv1_act,
    int32_t e_conv2_w, int32_t e_conv2_act,
    int32_t e_fc1_w, int32_t e_fc1_act,
    int32_t e_fc2_w,
    int8_t* scratch,
    uint32_t* timing  
) {
    // Start timing
    uint32_t start_cycles = rdcycle();
    
    printf("[JIT] Inference start\n");
    
    int8_t* conv1_out = scratch;
    int8_t* pool1_out = conv1_out + 16*28*28;
    int8_t* conv2_out = pool1_out + 16*14*14;
    int8_t* pool2_out = conv2_out + 32*14*14;
    int8_t* fc1_out = pool2_out + 32*7*7;
    
    // Allocate INT32 buffer for final logits
    int32_t* fc2_out = (int32_t*)(fc1_out + 128);
    
    // Conv1 + ReLU + MaxPool
    conv2d_int8(input, 28, 28, 1, w_conv1, b_conv1, conv1_out, 16, 
                e_in, e_conv1_w, e_conv1_act);
    maxpool2d_int8(conv1_out, pool1_out, 28, 28, 16);
    
    // Conv2 + ReLU + MaxPool
    conv2d_int8(pool1_out, 14, 14, 16, w_conv2, b_conv2, conv2_out, 32,
                e_conv1_act, e_conv2_w, e_conv2_act);
    maxpool2d_int8(conv2_out, pool2_out, 14, 14, 32);
    
    // FC1 + ReLU
    fc_int8(pool2_out, 1568, w_fc1, b_fc1, fc1_out, 128,
            e_conv2_act, e_fc1_w, e_fc1_act);
    
    // FC2 → INT32 logits
    fc_int32_p4simd(fc1_out, 128, w_fc2, b_fc2, fc2_out, 10,
             e_fc1_act, e_fc2_w);
    
    // End timing
    uint32_t end_cycles = rdcycle();
    uint32_t elapsed = end_cycles - start_cycles;
    
    // Store timing in output array
    timing[0] = elapsed;
    
    // Argmax
    int32_t max_val = fc2_out[0];
    int32_t max_idx = 0;
    for (int i = 1; i < 10; i++) {
        if (fc2_out[i] > max_val) {
            max_val = fc2_out[i];
            max_idx = i;
        }
    }
    
    printf("[JIT] Predicted: %d (logit: %d) | Cycles: %u\n", max_idx, max_val, elapsed);
    return max_idx;
}
