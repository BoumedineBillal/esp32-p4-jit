// simple.c - Single file test for backward compatibility

typedef int int32_t;
typedef unsigned int uint32_t;
typedef signed char int8_t;

static uint32_t counter = 0;

int32_t compute(int32_t a, int32_t b) {
    counter++;
    return (a + b) * counter;
}

uint32_t get_counter(void) {
    return counter;
}

/*
void call(){

    //volatile uint32_t *p = (volatile uint32_t )(volatile uint32_t *)0x40000000;
    //volatile int32_t  x1 = *(volatile int32_t *)0x50000000;
    int32_t  x1 = *(volatile int32_t *)0x50000000;
    int32_t  x2 = *(volatile int32_t *)0x50000004;
    
    int32_t out = compute(x1, x2);
    
    *(volatile int32_t *)0x50000008 = out;
}
*/


/*
void call() {
    int32_t *io = (volatile int32_t *)0x50000000;
    
    int32_t x1 = io[0];
    int32_t x2 = io[1];
    
    int32_t out = compute(x1, x2);
    
    io[2] = out;
}
*/


float compute2(int32_t a, float b, int32_t* c, int8_t d) {
    counter++;
    return (a + b) * counter + c[2] - d;
}


void call() {
    int32_t *io = (volatile int32_t *)0x50000000;
    
    int32_t  a = *(int32_t*)&  io[0];
    float    b = *(float*)&    io[1];
    int32_t* c = (int32_t*)    io[2];
    int8_t   d = *(int8_t*)&   io[3];
    
    float out = compute2(a, b, c, d);
    
    io[4] = *(int32_t*)& out;
}


















