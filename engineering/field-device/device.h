/* A field device in the style of a substation remote terminal unit: it reports switch positions
 * and line currents, and operates a switch on command. Every request and every reply carries an
 * HMAC-SHA256 tag and a counter, so a forged, altered or replayed command is refused.
 *
 * Request, 41 bytes:  version(1) function(1) point(2) value(1) counter(4) | tag(32)
 * Reply,   42 bytes:  version(1) status(1)   point(2) value(2) counter(4) | tag(32)
 * Multi-byte fields are big-endian. The tag covers every byte before it.
 */
#ifndef DEVICE_H
#define DEVICE_H

#include <stddef.h>
#include <stdint.h>

#include "sha256.h"

#define FD_VERSION 1
#define FD_KEY_LEN 32
#define FD_REQ_BODY 9
#define FD_REQ_LEN (FD_REQ_BODY + SHA256_DIGEST)
#define FD_RESP_BODY 10
#define FD_RESP_LEN (FD_RESP_BODY + SHA256_DIGEST)
#define FD_NUM_SWITCH 1      /* point 0: tie switch SW-12 */
#define FD_NUM_ANALOG 3      /* points 0-2: phase A current at CB-101, R-1011, SW-12, in tenths of an amp */

enum fd_function { FD_READ_ANALOG = 0x01, FD_READ_SWITCH = 0x02, FD_OPERATE = 0x05 };

enum fd_status {
    FD_OK = 0,
    /* refused before the tag checks out: the device sends nothing back */
    FD_BAD_LENGTH = 1,
    FD_BAD_TAG = 2,
    /* refused after the tag checks out: the device sends a signed reply saying why */
    FD_BAD_VERSION = 3,
    FD_REPLAY = 4,
    FD_BAD_FUNCTION = 5,
    FD_BAD_POINT = 6,
    FD_BAD_VALUE = 7,
};

typedef struct {
    hmac_sha256_key key;                   /* the key, as its precomputed HMAC state */
    uint32_t last_counter;                 /* highest counter accepted; would live in flash */
    uint8_t switch_closed[FD_NUM_SWITCH];
    uint16_t analog_da[FD_NUM_ANALOG];     /* what the sensors read, tenths of an amp */
    uint32_t accepted, refused;
} fd_device;

void fd_init(fd_device *d, const uint8_t key[FD_KEY_LEN]);

/* Handle one request. Returns the status. *resp_len is set to FD_RESP_LEN if a signed reply
 * was written to resp, or 0 if the device stays silent. */
int fd_handle(fd_device *d, const uint8_t *req, size_t len, uint8_t resp[FD_RESP_LEN], size_t *resp_len);

/* The control-center side: build a signed request. */
void fd_build_request(const uint8_t key[FD_KEY_LEN], uint8_t function, uint16_t point, uint8_t value,
                      uint32_t counter, uint8_t out[FD_REQ_LEN]);

#endif
