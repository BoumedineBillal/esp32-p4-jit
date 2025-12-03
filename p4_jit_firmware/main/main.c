#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "p4_jit.h"

static const char *TAG = "main";

void app_main(void)
{
    ESP_LOGI(TAG, "Starting P4-JIT Firmware (Component Mode)");

    // Start the JIT Engine in the background
    // It will use defaults from Kconfig if config is NULL
    ESP_ERROR_CHECK(p4_jit_start(NULL));

    ESP_LOGI(TAG, "JIT Engine started in background task.");

    // The main app continues running!
    while (1) {
        // Just a heartbeat to show main task is free
        vTaskDelay(pdMS_TO_TICKS(500000));
        ESP_LOGI(TAG, "Main app heartbeat...");
    }
}
