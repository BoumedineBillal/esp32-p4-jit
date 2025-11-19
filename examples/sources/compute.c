typedef int int32_t;
typedef unsigned int uint32_t;
typedef signed char int8_t;

static int32_t call_count = 1;
static int32_t total_sum;
static const int32_t multipliers[4] = {10, 20, 30, 40};

int32_t compute(int32_t a, int32_t b) {
    call_count++;
    
    int32_t sum = a + b;
    
    int32_t index = (call_count - 1) & 3;
    int32_t result = sum * multipliers[index];
    
    total_sum += result;
    
    return result;
}

int32_t get_call_count(void) {
    return call_count;
}

int32_t get_total_sum(void) {
    return total_sum;
}



int32_t c = 7;
int32_t e = 5;
int32_t k = 88;
int32_t d;

__attribute__((noinline))
int32_t mul(int32_t a, int32_t b) {

    __asm__ volatile("ESP.ZERO.QACC");

    return a*b;
}


int32_t add(int32_t a, int32_t b) {
    d = (a - 1) & 3;
    return a + b + c + d + mul(e , 2) + k;
}






int32_t add2(int32_t a, int32_t b) {
    return a + mul(b , 2);
}


/*
__attribute__((used))
float InterpolateWaveHermite(
        const float *table,
        const int32_t index_integral,
        const float index_fractional) {
    const float xm1 = table[index_integral];
    const float x0 = table[index_integral + 1];
    const float x1 = table[index_integral + 2];
    const float x2 = table[index_integral + 3];
    const float c = (x1 - xm1) * 0.5f;
    const float v = x0 - x1;
    const float w = c + v;
    const float a = w + v + (x2 - x0) * 0.5f;
    const float b_neg = w + a;
    const float f = index_fractional;
    return (((a * f) - b_neg) * f + c) * f + x0;
}   interpol
*/

float InterpolateWaveHermite(
        const float *table,
        const int32_t index_integral,
        const float index_fractional) {
    const float xm1 = table[index_integral];
    const float x0 = table[index_integral + 1];
    const float x1 = table[index_integral + 2];
    const float x2 = table[index_integral + 3];
    const float c = (x1 - xm1) * 0.5f;
    const float v = x0 - x1;
    const float w = c + v;
    const float a = w + v + (x2 - x0) * 0.5f;
    const float b_neg = w + a;
    const float f = index_fractional;
    return (((a * f) - b_neg) * f + c) * f + x0;
}











