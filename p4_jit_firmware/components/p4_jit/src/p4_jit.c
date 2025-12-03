#include "p4_jit.h"
#include "protocol.h"
#include "usb_transport.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "sdkconfig.h"

static const char *TAG = "p4_jit";
static TaskHandle_t s_jit_task_handle = NULL;

static void jit_task_entry(void *arg) {
    ESP_LOGI(TAG, "JIT Task started on Core %d", xPortGetCoreID());
    protocol_loop();
    // protocol_loop is infinite, but if it returns:
    vTaskDelete(NULL);
}

esp_err_t p4_jit_start(const p4_jit_config_t *config) {
    if (s_jit_task_handle != NULL) {
        ESP_LOGW(TAG, "JIT engine already running");
        return ESP_ERR_INVALID_STATE;
    }

    // Defaults
    int priority = CONFIG_P4_JIT_TASK_PRIORITY;
    int core_id = CONFIG_P4_JIT_TASK_CORE_ID;
    int stack_size = CONFIG_P4_JIT_TASK_STACK_SIZE;

    if (config) {
        if (config->task_priority > 0) priority = config->task_priority;
        if (config->task_core_id >= -1) core_id = config->task_core_id;
        if (config->stack_size > 0) stack_size = config->stack_size;
    }

    ESP_LOGI(TAG, "Initializing USB Transport...");
    usb_transport_init();

    ESP_LOGI(TAG, "Starting JIT Task (Prio:%d, Core:%d, Stack:%d)", priority, core_id, stack_size);
    
    BaseType_t ret = xTaskCreatePinnedToCore(
        jit_task_entry,
        "jit_task",
        stack_size,
        NULL,
        priority,
        &s_jit_task_handle,
        core_id
    );

    if (ret != pdPASS) {
        ESP_LOGE(TAG, "Failed to create JIT task");
        return ESP_FAIL;
    }

    return ESP_OK;
}

esp_err_t p4_jit_stop(void) {
    if (s_jit_task_handle) {
        vTaskDelete(s_jit_task_handle);
        s_jit_task_handle = NULL;
    }
    return ESP_OK;
}
