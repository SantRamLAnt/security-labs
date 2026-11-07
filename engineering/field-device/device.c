#include "device.h"

#include <string.h>

static uint32_t load_be32(const uint8_t *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}

static void store_be32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)(v >> 24); p[1] = (uint8_t)(v >> 16); p[2] = (uint8_t)(v >> 8); p[3] = (uint8_t)v;
}

void fd_init(fd_device *d, const uint8_t key[FD_KEY_LEN]) {
    memset(d, 0, sizeof *d);
    hmac_sha256_setkey(&d->key, key, FD_KEY_LEN);
}

static void sign_reply(const fd_device *d, uint8_t status, uint16_t point, uint16_t value,
                       uint32_t counter, uint8_t resp[FD_RESP_LEN]) {
    resp[0] = FD_VERSION;
    resp[1] = status;
    resp[2] = (uint8_t)(point >> 8); resp[3] = (uint8_t)point;
    resp[4] = (uint8_t)(value >> 8); resp[5] = (uint8_t)value;
    store_be32(resp + 6, counter);
    hmac_sha256_mac(&d->key, resp, FD_RESP_BODY, resp + FD_RESP_BODY);
}

int fd_handle(fd_device *d, const uint8_t *req, size_t len, uint8_t resp[FD_RESP_LEN], size_t *resp_len) {
    *resp_len = 0;

    /* 1. Exact length. Nothing else in the frame is read until the tag is checked. */
    if (len != FD_REQ_LEN) { d->refused++; return FD_BAD_LENGTH; }

    /* 2. The tag, compared in constant time. A wrong tag gets no reply at all, so a forger
     *    learns nothing from the device. */
    uint8_t tag[SHA256_DIGEST];
    hmac_sha256_mac(&d->key, req, FD_REQ_BODY, tag);
    if (!equal_ct(tag, req + FD_REQ_BODY, SHA256_DIGEST)) { d->refused++; return FD_BAD_TAG; }

    uint8_t version = req[0], function = req[1], value = req[4];
    uint16_t point = (uint16_t)((req[2] << 8) | req[3]);
    uint32_t counter = load_be32(req + 5);

    /* 3. Freshness. The counter must go up. A recorded command played back later carries an old
     *    counter and is refused, even though its tag is genuine. */
    if (counter <= d->last_counter) {
        d->refused++;
        sign_reply(d, FD_REPLAY, point, 0, counter, resp);
        *resp_len = FD_RESP_LEN;
        return FD_REPLAY;
    }
    d->last_counter = counter;   /* consumed even if the request turns out to be invalid */

    int status = FD_OK;
    uint16_t out = 0;
    if (version != FD_VERSION) {
        status = FD_BAD_VERSION;
    } else if (function == FD_READ_ANALOG) {
        if (point >= FD_NUM_ANALOG) status = FD_BAD_POINT;
        else out = d->analog_da[point];
    } else if (function == FD_READ_SWITCH) {
        if (point >= FD_NUM_SWITCH) status = FD_BAD_POINT;
        else out = d->switch_closed[point];
    } else if (function == FD_OPERATE) {
        if (point >= FD_NUM_SWITCH) status = FD_BAD_POINT;
        else if (value > 1) status = FD_BAD_VALUE;
        else { d->switch_closed[point] = value; out = value; }
    } else {
        status = FD_BAD_FUNCTION;
    }
    if (status == FD_OK) d->accepted++;
    else d->refused++;
    sign_reply(d, (uint8_t)status, point, out, counter, resp);
    *resp_len = FD_RESP_LEN;
    return status;
}

void fd_build_request(const uint8_t key[FD_KEY_LEN], uint8_t function, uint16_t point, uint8_t value,
                      uint32_t counter, uint8_t out[FD_REQ_LEN]) {
    out[0] = FD_VERSION;
    out[1] = function;
    out[2] = (uint8_t)(point >> 8); out[3] = (uint8_t)point;
    out[4] = value;
    store_be32(out + 5, counter);
    hmac_sha256(key, FD_KEY_LEN, out, FD_REQ_BODY, out + FD_REQ_BODY);
}
