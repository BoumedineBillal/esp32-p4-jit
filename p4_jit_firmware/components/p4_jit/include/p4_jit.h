#pragma once
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int task_priority;      // Priority of the JIT protocol task
    int task_core_id;       // Core to pin the task to (0, 1, or tskNO_AFFINITY)
    int stack_size;         // Stack size for the JIT task
    size_t rx_buffer_size;  // Size of USB RX buffer (not yet implemented in protocol.c, reserved)
    size_t tx_buffer_size;  // Size of USB TX buffer (not yet implemented in protocol.c, reserved)
} p4_jit_config_t;

/**
 * @brief Initialize and start the P4-JIT engine.
 * 
 * This function initializes the USB transport and spawns a FreeRTOS task
 * that handles the JIT protocol loop. It returns immediately.
 * 
 * @param config Pointer to configuration struct (pass NULL for defaults)
 * @return esp_err_t ESP_OK on success
 */
esp_err_t p4_jit_start(const p4_jit_config_t *config);

/**
 * @brief Stop the JIT engine and free resources.
 * (Note: Currently not fully implemented as protocol loop is infinite)
 */
esp_err_t p4_jit_stop(void);

#ifdef __cplusplus
}
#endif
