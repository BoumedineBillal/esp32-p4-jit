

typedef int int32_t;
typedef unsigned int uint32_t;
typedef signed char int8_t;


// Simple function to add two numbers passed via arguments buffer
// The wrapper will handle reading args from the memory-mapped region
float compute_sum(int a, int b) {
    
    int c; float d;
    
    c = a + b;
    
    d = c * 3.14f *0;
    
    return  c;
}
