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


void call(){

    //volatile uint32_t *p = (volatile uint32_t )(volatile uint32_t *)0x40000000;
    volatile int32_t  x1 = *(volatile int32_t *)0x50000000;
    volatile int32_t  x2 = *(volatile int32_t *)0x50000003;
    
    int32_t out = compute(x1, x2);
    
    *(volatile int32_t *)0x50000007 = out;
}
