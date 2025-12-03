#include "sdkconfig.h"
#include "usb_transport.h"
#include "esp_log.h"
#include "tinyusb.h"
#include "tinyusb_cdc_acm.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/stream_buffer.h"

static const char *TAG = "usb_transport";
static StreamBufferHandle_t rx_stream_buffer = NULL;

// Buffer for ISR callback to read into before sending to stream buffer
#define RX_BUF_SIZE 2048
static uint8_t rx_temp_buf[RX_BUF_SIZE];

static void rx_callback(int itf, cdcacm_event_t *event)
{
    size_t rx_size = 0;
    
    // Read from TinyUSB internal buffer
    esp_err_t ret = tinyusb_cdcacm_read(itf, rx_temp_buf, RX_BUF_SIZE, &rx_size);
    if (ret == ESP_OK && rx_size > 0) {
        // Send to StreamBuffer
        // We use a short timeout (0) because this is a callback (context might be ISR or Task depending on stack)
        // TinyUSB callbacks are usually in a task context (tusb task), so we can block slightly or just fail.
        // But xStreamBufferSend is safe.
        size_t sent = xStreamBufferSend(rx_stream_buffer, rx_temp_buf, rx_size, 0);
        if (sent != rx_size) {
            ESP_LOGW(TAG, "StreamBuffer overflow, dropped %d bytes", rx_size - sent);
        }
    }
}

void usb_transport_init(void)
{
    ESP_LOGI(TAG, "Initializing USB Transport...");

    // 1. Create Stream Buffer
    // Use configured buffer size or default to 16KB if not set
    #ifndef CONFIG_P4_JIT_STREAM_BUFFER_SIZE
    #define CONFIG_P4_JIT_STREAM_BUFFER_SIZE (16 * 1024)
    #endif
    
    rx_stream_buffer = xStreamBufferCreate(CONFIG_P4_JIT_STREAM_BUFFER_SIZE, 1);
    if (rx_stream_buffer == NULL) {
        ESP_LOGE(TAG, "Failed to create stream buffer");
        abort();
    }
    ESP_LOGI(TAG, "Stream buffer created");

    // 2. Install TinyUSB Driver
    const tinyusb_config_t tusb_cfg = {
        .port = TINYUSB_PORT_HIGH_SPEED_0, 
        .task = {
            .size = 4096,
            .priority = 5,
            .xCoreID = 0,
        },
    };
    ESP_ERROR_CHECK(tinyusb_driver_install(&tusb_cfg));
    ESP_LOGI(TAG, "TinyUSB driver installed");

    // 3. Initialize CDC-ACM
    tinyusb_config_cdcacm_t acm_cfg = {
        .cdc_port = TINYUSB_CDC_ACM_0,
        .callback_rx = &rx_callback,
        .callback_rx_wanted_char = NULL,
        .callback_line_state_changed = NULL,
        .callback_line_coding_changed = NULL
    };
    ESP_ERROR_CHECK(tinyusb_cdcacm_init(&acm_cfg));

    ESP_LOGI(TAG, "USB Initialized");
}

void usb_read_bytes(uint8_t *buffer, size_t len)
{
    // ESP_LOGI(TAG, "Reading %d bytes...", len); // Too spammy?
    size_t received = 0;
    while (received < len) {
        // Block until at least 1 byte is available
        size_t xBytesReceived = xStreamBufferReceive(rx_stream_buffer, 
                                                     buffer + received, 
                                                     len - received, 
                                                     portMAX_DELAY);
        received += xBytesReceived;
        // ESP_LOGI(TAG, "Received chunk: %d, total: %d/%d", xBytesReceived, received, len);
    }
    // ESP_LOGI(TAG, "Read complete");
}

void usb_write_bytes(const uint8_t *buffer, size_t len)
{
    size_t sent = 0;
    while (sent < len) {
        size_t remaining = len - sent;
        // Write queue returns amount actually queued
        size_t queued = tinyusb_cdcacm_write_queue(TINYUSB_CDC_ACM_0, buffer + sent, remaining);
        
        if (queued > 0) {
            tinyusb_cdcacm_write_flush(TINYUSB_CDC_ACM_0, 0);
            sent += queued;
        } else {
            // Buffer full, wait a bit
            vTaskDelay(pdMS_TO_TICKS(1));
        }
    }
    tinyusb_cdcacm_write_flush(TINYUSB_CDC_ACM_0, 0);
}
