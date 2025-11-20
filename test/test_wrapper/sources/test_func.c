// test_func.c - Test function for wrapper generation

typedef int int32_t;
typedef unsigned int uint32_t;
typedef signed char int8_t;

static uint32_t counter = 0;

float compute2(int32_t a, float b, int32_t* c, int8_t d) {
    counter++;
    return (a + b) * counter + c[2] - d;
}




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