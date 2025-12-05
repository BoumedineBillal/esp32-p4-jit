#include <stdint.h>
#include <string.h>


// Function to sum elements of an int8 array
// Args:
//   arr: Pointer to the array in memory
//   len: Number of elements
int sum_array(int8_t *arr, int len) {
    int sum = 0;
    for (int i = 0; i < len; i++) {
        sum += arr[i];
    }
    
    // Fake usage to trigger linker error with -nostdlib
    //char buf[10];
    //memset(buf, 7, 10);  // ERROR: undefined reference to `memset`
    
    return sum ;//+ (int)buf[0];
}
