#pragma once

#include <stdint.h>
#include <stddef.h>

// Command IDs
#define CMD_PING        0x01
#define CMD_ALLOC       0x10
#define CMD_FREE        0x11
#define CMD_WRITE_MEM   0x20
#define CMD_READ_MEM    0x21
#define CMD_EXEC        0x30

// Error Codes
#define ERR_OK          0x00
#define ERR_CHECKSUM    0x01
#define ERR_UNKNOWN_CMD 0x02
#define ERR_ALLOC_FAIL  0x03

/**
 * @brief Dispatch a command based on ID.
 * 
 * @param cmd_id Command ID
 * @param payload Input payload buffer
 * @param len Input payload length
 * @param out_payload Output payload buffer (pre-allocated)
 * @param out_len Pointer to store output length
 * @return Error code (0 = OK)
 */
uint32_t dispatch_command(uint8_t cmd_id, uint8_t *payload, uint32_t len, uint8_t *out_payload, uint32_t *out_len);
