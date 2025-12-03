#include "commands.h"
#include "esp_log.h"
#include "esp_heap_caps.h"
#include "esp_cache.h"
#include <string.h>

static const char *TAG = "commands";

// Helper structs for parsing payloads
#pragma pack(push, 1)
typedef struct {
    uint32_t size;
    // uint8_t memory_type; // Removed
    uint32_t caps;
    uint32_t alignment;
} cmd_alloc_req_t;

typedef struct {
    uint32_t address;
    uint32_t error_code;
} cmd_alloc_resp_t;

typedef struct {
    uint32_t address;
} cmd_free_req_t;

typedef struct {
    uint32_t address;
    // data follows
} cmd_write_req_t;

typedef struct {
    uint32_t bytes_written;
    uint32_t status;
} cmd_write_resp_t;

typedef struct {
    uint32_t address;
    uint32_t size;
} cmd_read_req_t;

typedef struct {
    uint32_t address;
} cmd_exec_req_t;

typedef struct {
    uint32_t return_value;
} cmd_exec_resp_t;
#pragma pack(pop)

uint32_t dispatch_command(uint8_t cmd_id, uint8_t *payload, uint32_t len, uint8_t *out_payload, uint32_t *out_len) {
    switch (cmd_id) {
        case CMD_PING:
            if (len > 0) memcpy(out_payload, payload, len);
            *out_len = len;
            return ERR_OK;

        case CMD_ALLOC: {
            if (len < sizeof(cmd_alloc_req_t)) {
                ESP_LOGE(TAG, "CMD_ALLOC: Payload too short (%lu)", len);
                return ERR_UNKNOWN_CMD; 
            }
            cmd_alloc_req_t *req = (cmd_alloc_req_t*)payload;
            
            ESP_LOGI(TAG, "CMD_ALLOC: Size=%lu, Caps=0x%08lX, Align=%lu", 
                     req->size, req->caps, req->alignment);

            void *ptr = heap_caps_aligned_alloc(req->alignment, req->size, req->caps);
            
            if (ptr) {
                ESP_LOGI(TAG, "CMD_ALLOC: Success at %p", ptr);
            } else {
                ESP_LOGE(TAG, "CMD_ALLOC: Failed");
            }

            cmd_alloc_resp_t *resp = (cmd_alloc_resp_t*)out_payload;
            resp->address = (uint32_t)ptr;
            resp->error_code = (ptr != NULL) ? 0 : ERR_ALLOC_FAIL;
            
            *out_len = sizeof(cmd_alloc_resp_t);
            return ERR_OK;
        }

        case CMD_FREE: {
            if (len < sizeof(cmd_free_req_t)) return ERR_UNKNOWN_CMD;
            cmd_free_req_t *req = (cmd_free_req_t*)payload;
            
            heap_caps_free((void*)req->address);
            
            // Response is just status 0 (handled by dispatch return)
            uint32_t *status = (uint32_t*)out_payload;
            *status = 0;
            *out_len = 4;
            return ERR_OK;
        }

        case CMD_WRITE_MEM: {
            if (len < sizeof(cmd_write_req_t)) return ERR_UNKNOWN_CMD;
            cmd_write_req_t *req = (cmd_write_req_t*)payload;
            uint32_t data_len = len - sizeof(cmd_write_req_t);
            uint8_t *data_ptr = payload + sizeof(cmd_write_req_t);

            memcpy((void*)req->address, data_ptr, data_len);

            // Sync Cache (D-Cache -> RAM -> I-Cache)
            // esp_cache_msync requires address and size to be aligned to cache line size (128 bytes on P4)
            #define CACHE_LINE_SIZE 128
            uint32_t start_addr = req->address;
            uint32_t end_addr = start_addr + data_len;
            
            uint32_t aligned_start = start_addr & ~(CACHE_LINE_SIZE - 1);
            uint32_t aligned_end = (end_addr + CACHE_LINE_SIZE - 1) & ~(CACHE_LINE_SIZE - 1);
            uint32_t aligned_size = aligned_end - aligned_start;
            
            ESP_LOGI(TAG, "Cache Sync: Orig Addr=0x%08lX, Len=0x%lX -> Aligned Addr=0x%08lX, Len=0x%lX", 
                     req->address, data_len, aligned_start, aligned_size);

            esp_err_t err = esp_cache_msync((void*)aligned_start, aligned_size, 
                                          ESP_CACHE_MSYNC_FLAG_DIR_C2M | ESP_CACHE_MSYNC_FLAG_INVALIDATE);
            if (err != ESP_OK) {
                ESP_LOGE(TAG, "Cache sync failed: 0x%x", err);
            }

            cmd_write_resp_t *resp = (cmd_write_resp_t*)out_payload;
            resp->bytes_written = data_len;
            resp->status = (err == ESP_OK) ? 0 : 1;
            *out_len = sizeof(cmd_write_resp_t);
            return ERR_OK;
        }

        case CMD_READ_MEM: {
            if (len < sizeof(cmd_read_req_t)) return ERR_UNKNOWN_CMD;
            cmd_read_req_t *req = (cmd_read_req_t*)payload;
            
            // Safety check? Python side handles it, but we could check if readable.
            // For now, blind memcpy.
            memcpy(out_payload, (void*)req->address, req->size);
            
            *out_len = req->size;
            return ERR_OK;
        }

        case CMD_EXEC: {
            if (len < sizeof(cmd_exec_req_t)) return ERR_UNKNOWN_CMD;
            cmd_exec_req_t *req = (cmd_exec_req_t*)payload;

            // Cast and call
            typedef int (*jit_func_t)(void);
            jit_func_t func = (jit_func_t)req->address;
            
            ESP_LOGI(TAG, "Executing at 0x%08lX", req->address);
            int ret = func();
            ESP_LOGI(TAG, "Returned: %d", ret);

            cmd_exec_resp_t *resp = (cmd_exec_resp_t*)out_payload;
            resp->return_value = ret;
            *out_len = sizeof(cmd_exec_resp_t);
            return ERR_OK;
        }

        default:
            ESP_LOGW(TAG, "Unknown command: 0x%02X", cmd_id);
            return ERR_UNKNOWN_CMD;
    }
}
