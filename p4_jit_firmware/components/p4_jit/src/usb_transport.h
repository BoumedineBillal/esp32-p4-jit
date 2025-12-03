#pragma once

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

/**
 * @brief Initialize the TinyUSB CDC stack.
 */
void usb_transport_init(void);

/**
 * @brief Read bytes from USB CDC. Blocks until all requested bytes are received.
 * 
 * @param buffer Destination buffer
 * @param len Number of bytes to read
 */
void usb_read_bytes(uint8_t *buffer, size_t len);

/**
 * @brief Write bytes to USB CDC. Blocks until bytes are queued.
 * 
 * @param buffer Source buffer
 * @param len Number of bytes to write
 */
void usb_write_bytes(const uint8_t *buffer, size_t len);
