// simple.c - Single file test for backward compatibility

typedef int int32_t;
typedef unsigned int uint32_t;

static uint32_t counter = 0;

int32_t compute(int32_t a, int32_t b) {
    counter++;
    return (a + b) * counter;
}

uint32_t get_counter(void) {
    return counter;
}
