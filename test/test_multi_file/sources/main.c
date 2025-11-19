// main.c - Entry point for multi-file test

typedef int int32_t;
typedef unsigned int uint32_t;

// External functions from other files
extern int32_t add_numbers(int32_t a, int32_t b);
extern int32_t multiply_numbers(int32_t a, int32_t b);
extern int32_t vector_dot_product(int32_t x1, int32_t y1, int32_t x2, int32_t y2);

// Static data
static uint32_t call_counter = 0;

int32_t main(int32_t x, int32_t y) {
    call_counter++;
    
    int32_t sum = add_numbers(x, y);
    int32_t product = multiply_numbers(x, y);
    int32_t dot = vector_dot_product(x, y, sum, product);
    
    return dot + call_counter;
}

uint32_t get_call_count(void) {
    return call_counter;
}
