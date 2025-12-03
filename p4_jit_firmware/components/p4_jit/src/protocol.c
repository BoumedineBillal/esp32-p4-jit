#include "protocol.h"
#include "usb_transport.h"
#include "commands.h"
#include "esp_log.h"
#include <string.h>
#include <stdlib.h>

static const char *TAG = "protocol";

#define MAGIC_BYTE_1 0xA5
#define MAGIC_BYTE_2 0x5A

#pragma pack(push, 1)
typedef struct {
    uint8_t magic[2];
    uint8_t cmd_id;
    uint8_t flags;
    uint32_t payload_len;
} packet_header_t;
#pragma pack(pop)

// Max payload size (1MB + overhead)
#ifdef CONFIG_P4_JIT_PAYLOAD_BUFFER_SIZE
#define MAX_PAYLOAD_SIZE (CONFIG_P4_JIT_PAYLOAD_BUFFER_SIZE + 1024)
#else
#define MAX_PAYLOAD_SIZE (1024 * 1024 + 1024)
#endif
static uint8_t *rx_buffer = NULL;
static uint8_t *tx_buffer = NULL;

static uint16_t calculate_checksum(const uint8_t *data, size_t len) {
    uint16_t sum = 0;
    for (size_t i = 0; i < len; i++) {
        sum += data[i];
    }
    return sum;
}

void send_response(uint8_t cmd_id, uint8_t flags, uint8_t *payload, uint32_t len) {
    packet_header_t header;
    header.magic[0] = MAGIC_BYTE_1;
    header.magic[1] = MAGIC_BYTE_2;
    header.cmd_id = cmd_id;
    header.flags = flags;
    header.payload_len = len;

    // Calculate checksum (Header + Payload)
    uint16_t checksum = 0;
    checksum += calculate_checksum((uint8_t*)&header, sizeof(header));
    if (payload && len > 0) {
        checksum += calculate_checksum(payload, len);
    }

    usb_write_bytes((uint8_t*)&header, sizeof(header));
    if (payload && len > 0) {
        usb_write_bytes(payload, len);
    }
    usb_write_bytes((uint8_t*)&checksum, 2);
}

void protocol_loop(void) {
    // Allocate buffers in PSRAM if possible, or SRAM
    // For now, let's use malloc. In a real scenario, we might want specific caps.
    rx_buffer = malloc(MAX_PAYLOAD_SIZE);
    tx_buffer = malloc(MAX_PAYLOAD_SIZE);
    
    if (!rx_buffer || !tx_buffer) {
        ESP_LOGE(TAG, "Failed to allocate buffers");
        return;
    }

    ESP_LOGI(TAG, "Protocol loop started");

    while (1) {
        // 1. Sync: Look for Magic
        uint8_t byte;
        usb_read_bytes(&byte, 1);
        if (byte != MAGIC_BYTE_1) continue;
        
        usb_read_bytes(&byte, 1);
        if (byte != MAGIC_BYTE_2) continue;

        // 2. Read rest of header
        packet_header_t header;
        header.magic[0] = MAGIC_BYTE_1;
        header.magic[1] = MAGIC_BYTE_2;
        usb_read_bytes(&header.cmd_id, 1);
        usb_read_bytes(&header.flags, 1);
        usb_read_bytes((uint8_t*)&header.payload_len, 4);

        // 3. Read Payload
        if (header.payload_len > MAX_PAYLOAD_SIZE) {
            ESP_LOGE(TAG, "Payload too large: %lu", header.payload_len);
            // Flush? Or just reset loop.
            continue; 
        }
        if (header.payload_len > 0) {
            usb_read_bytes(rx_buffer, header.payload_len);
        }

        // 4. Read Checksum
        uint16_t received_checksum;
        usb_read_bytes((uint8_t*)&received_checksum, 2);

        // 5. Verify Checksum
        uint16_t calc_checksum = calculate_checksum((uint8_t*)&header, sizeof(header));
        if (header.payload_len > 0) {
            calc_checksum += calculate_checksum(rx_buffer, header.payload_len);
        }

        if (calc_checksum != received_checksum) {
            ESP_LOGE(TAG, "Checksum mismatch: Calc %04X != Recv %04X", calc_checksum, received_checksum);
            // Send Error Response
            uint32_t err = ERR_CHECKSUM;
            send_response(header.cmd_id, 0x02, (uint8_t*)&err, 4);
            continue;
        }

        // 6. Dispatch
        ESP_LOGI(TAG, "Dispatching CMD: 0x%02X, Payload: %lu bytes", header.cmd_id, header.payload_len);
        uint32_t out_len = 0;
        uint32_t err_code = dispatch_command(header.cmd_id, rx_buffer, header.payload_len, tx_buffer, &out_len);

        if (err_code != ERR_OK) {
             ESP_LOGE(TAG, "Command failed with error: 0x%02X", err_code);
             send_response(header.cmd_id, 0x02, (uint8_t*)&err_code, 4);
        } else {
             ESP_LOGI(TAG, "Command success, sending response: %lu bytes", out_len);
             send_response(header.cmd_id, 0x01, tx_buffer, out_len);
        }
    }
}
