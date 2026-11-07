/* SHA-256 following FIPS 180-4, sections 4.1.2 (functions), 4.2.2 (constants), 5.1.1 (padding),
 * 5.3.3 (initial hash value) and 6.2.2 (the hash computation). */
#include "sha256.h"

#include <string.h>

static const uint32_t K[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};

#define ROTR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))
#define CH(x, y, z) (((x) & (y)) ^ (~(x) & (z)))
#define MAJ(x, y, z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define BSIG0(x) (ROTR(x, 2) ^ ROTR(x, 13) ^ ROTR(x, 22))
#define BSIG1(x) (ROTR(x, 6) ^ ROTR(x, 11) ^ ROTR(x, 25))
#define SSIG0(x) (ROTR(x, 7) ^ ROTR(x, 18) ^ ((x) >> 3))
#define SSIG1(x) (ROTR(x, 17) ^ ROTR(x, 19) ^ ((x) >> 10))

/* Read and write 32-bit words big-endian one byte at a time, so the result is the same on a
 * little-endian Cortex-M0+ and on a PC. */
static uint32_t load_be32(const uint8_t *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}

static void store_be32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)(v >> 24); p[1] = (uint8_t)(v >> 16); p[2] = (uint8_t)(v >> 8); p[3] = (uint8_t)v;
}

static void compress(uint32_t h[8], const uint8_t block[64]) {
    uint32_t w[64];
    for (int t = 0; t < 16; t++) w[t] = load_be32(block + 4 * t);
    for (int t = 16; t < 64; t++) w[t] = SSIG1(w[t - 2]) + w[t - 7] + SSIG0(w[t - 15]) + w[t - 16];

    uint32_t a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
    for (int t = 0; t < 64; t++) {
        uint32_t t1 = hh + BSIG1(e) + CH(e, f, g) + K[t] + w[t];
        uint32_t t2 = BSIG0(a) + MAJ(a, b, c);
        hh = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
}

void sha256_init(sha256_ctx *c) {
    static const uint32_t H0[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                                   0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    memcpy(c->h, H0, sizeof H0);
    c->bits = 0;
    c->used = 0;
}

void sha256_update(sha256_ctx *c, const uint8_t *data, size_t len) {
    c->bits += (uint64_t)len * 8;
    while (len > 0) {
        size_t take = SHA256_BLOCK - c->used;
        if (take > len) take = len;
        memcpy(c->buf + c->used, data, take);
        c->used += take; data += take; len -= take;
        if (c->used == SHA256_BLOCK) {
            compress(c->h, c->buf);
            c->used = 0;
        }
    }
}

void sha256_final(sha256_ctx *c, uint8_t out[SHA256_DIGEST]) {
    /* Padding: a 1 bit, zeros, then the 64-bit length, ending on a block boundary. If fewer than
     * 9 bytes are left in this block, the length spills into one more block. */
    uint64_t bits = c->bits;
    c->buf[c->used++] = 0x80;
    if (c->used > 56) {
        memset(c->buf + c->used, 0, SHA256_BLOCK - c->used);
        compress(c->h, c->buf);
        c->used = 0;
    }
    memset(c->buf + c->used, 0, 56 - c->used);
    store_be32(c->buf + 56, (uint32_t)(bits >> 32));
    store_be32(c->buf + 60, (uint32_t)bits);
    compress(c->h, c->buf);
    for (int i = 0; i < 8; i++) store_be32(out + 4 * i, c->h[i]);
    memset(c, 0, sizeof *c);   /* don't leave key-dependent state behind in RAM */
}

void sha256(const uint8_t *data, size_t len, uint8_t out[SHA256_DIGEST]) {
    sha256_ctx c;
    sha256_init(&c);
    sha256_update(&c, data, len);
    sha256_final(&c, out);
}

/* HMAC (RFC 2104): H((K ^ opad) || H((K ^ ipad) || message)). A key longer than one block is
 * hashed first; a shorter one is padded with zeros. */
void hmac_sha256(const uint8_t *key, size_t key_len, const uint8_t *msg, size_t msg_len,
                 uint8_t out[SHA256_DIGEST]) {
    uint8_t k[SHA256_BLOCK] = {0}, pad[SHA256_BLOCK], inner[SHA256_DIGEST];
    if (key_len > SHA256_BLOCK) sha256(key, key_len, k);
    else memcpy(k, key, key_len);

    sha256_ctx c;
    for (int i = 0; i < SHA256_BLOCK; i++) pad[i] = k[i] ^ 0x36;
    sha256_init(&c);
    sha256_update(&c, pad, SHA256_BLOCK);
    sha256_update(&c, msg, msg_len);
    sha256_final(&c, inner);

    for (int i = 0; i < SHA256_BLOCK; i++) pad[i] = k[i] ^ 0x5c;
    sha256_init(&c);
    sha256_update(&c, pad, SHA256_BLOCK);
    sha256_update(&c, inner, SHA256_DIGEST);
    sha256_final(&c, out);

    memset(k, 0, sizeof k);
    memset(pad, 0, sizeof pad);
}

void hmac_sha256_setkey(hmac_sha256_key *hk, const uint8_t *key, size_t key_len) {
    uint8_t k[SHA256_BLOCK] = {0}, pad[SHA256_BLOCK];
    if (key_len > SHA256_BLOCK) sha256(key, key_len, k);
    else memcpy(k, key, key_len);
    for (int i = 0; i < SHA256_BLOCK; i++) pad[i] = k[i] ^ 0x36;
    sha256_init(&hk->inner);
    sha256_update(&hk->inner, pad, SHA256_BLOCK);      /* one compression, done once */
    for (int i = 0; i < SHA256_BLOCK; i++) pad[i] = k[i] ^ 0x5c;
    sha256_init(&hk->outer);
    sha256_update(&hk->outer, pad, SHA256_BLOCK);
    memset(k, 0, sizeof k);
    memset(pad, 0, sizeof pad);
}

void hmac_sha256_mac(const hmac_sha256_key *hk, const uint8_t *msg, size_t msg_len, uint8_t out[SHA256_DIGEST]) {
    uint8_t inner[SHA256_DIGEST];
    sha256_ctx c = hk->inner;                           /* copy: the saved state is reused */
    sha256_update(&c, msg, msg_len);
    sha256_final(&c, inner);
    c = hk->outer;
    sha256_update(&c, inner, SHA256_DIGEST);
    sha256_final(&c, out);
}

int equal_ct(const uint8_t *a, const uint8_t *b, size_t len) {
    uint8_t diff = 0;
    for (size_t i = 0; i < len; i++) diff |= (uint8_t)(a[i] ^ b[i]);
    return diff == 0;
}
