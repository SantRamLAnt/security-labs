/* SHA-256 (FIPS 180-4) and HMAC-SHA256 (RFC 2104), written for a small microcontroller:
 * no heap, no floating point, fixed-size state, and no dependence on the host's byte order. */
#ifndef SHA256_H
#define SHA256_H

#include <stddef.h>
#include <stdint.h>

#define SHA256_BLOCK 64
#define SHA256_DIGEST 32

typedef struct {
    uint32_t h[8];          /* the running hash value H(i) */
    uint64_t bits;          /* message length so far, in bits */
    uint8_t buf[SHA256_BLOCK];
    size_t used;            /* bytes waiting in buf */
} sha256_ctx;

void sha256_init(sha256_ctx *c);
void sha256_update(sha256_ctx *c, const uint8_t *data, size_t len);
void sha256_final(sha256_ctx *c, uint8_t out[SHA256_DIGEST]);
void sha256(const uint8_t *data, size_t len, uint8_t out[SHA256_DIGEST]);

void hmac_sha256(const uint8_t *key, size_t key_len, const uint8_t *msg, size_t msg_len,
                 uint8_t out[SHA256_DIGEST]);

/* The same HMAC with the key's two padded blocks hashed once, up front. Each tag then costs two
 * compression-function calls instead of four for a short message. The saved state is as secret
 * as the key itself. */
typedef struct {
    sha256_ctx inner, outer;
} hmac_sha256_key;

void hmac_sha256_setkey(hmac_sha256_key *k, const uint8_t *key, size_t key_len);
void hmac_sha256_mac(const hmac_sha256_key *k, const uint8_t *msg, size_t msg_len, uint8_t out[SHA256_DIGEST]);

/* Compare two buffers in time that depends only on the length, never on where they differ,
 * so an attacker can't learn a correct tag one byte at a time by timing the replies. */
int equal_ct(const uint8_t *a, const uint8_t *b, size_t len);

#endif
