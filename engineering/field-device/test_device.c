/* Tests for the field device. Build with -fsanitize=address,undefined to catch any out-of-bounds
 * access or undefined behavior during the fuzzing. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "device.h"

static int failures = 0;
#define CHECK(cond, ...) do { if (cond) { printf("  ok    "); } else { printf("  FAIL  "); failures++; } \
                              printf(__VA_ARGS__); printf("\n"); } while (0)

static void hex(const uint8_t *b, size_t n, char *out) {
    for (size_t i = 0; i < n; i++) sprintf(out + 2 * i, "%02x", b[i]);
}

static int digest_is(const uint8_t *d, const char *want) {
    char h[65];
    hex(d, 32, h);
    return strcmp(h, want) == 0;
}

/* xorshift64: a small, seeded generator so the fuzz run is repeatable */
static uint64_t rng = 20261106;
static uint64_t next(void) { rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17; return rng; }

static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}

static void test_sha256(void) {
    printf("SHA-256 against the FIPS 180-4 example messages\n");
    uint8_t d[32];
    sha256((const uint8_t *)"", 0, d);
    CHECK(digest_is(d, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"), "empty message");
    sha256((const uint8_t *)"abc", 3, d);
    CHECK(digest_is(d, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"), "\"abc\" (one block)");
    const char *m2 = "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq";
    sha256((const uint8_t *)m2, strlen(m2), d);
    CHECK(digest_is(d, "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"),
          "448-bit message (padding spills into a second block)");
    const char *m3 = "abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu";
    sha256((const uint8_t *)m3, strlen(m3), d);
    CHECK(digest_is(d, "cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1"), "896-bit message");
    sha256_ctx c;
    uint8_t a[1000];
    memset(a, 'a', sizeof a);
    sha256_init(&c);
    for (int i = 0; i < 1000; i++) sha256_update(&c, a, sizeof a);
    sha256_final(&c, d);
    CHECK(digest_is(d, "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"),
          "one million 'a' characters, fed 1,000 bytes at a time");
}

static void test_hmac(void) {
    printf("\nHMAC-SHA256 against RFC 4231\n");
    uint8_t d[32], key[131], msg[50];
    memset(key, 0x0b, 20);
    hmac_sha256(key, 20, (const uint8_t *)"Hi There", 8, d);
    CHECK(digest_is(d, "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"), "test case 1");
    hmac_sha256((const uint8_t *)"Jefe", 4, (const uint8_t *)"what do ya want for nothing?", 28, d);
    CHECK(digest_is(d, "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"), "test case 2 (short key)");
    memset(key, 0xaa, 20); memset(msg, 0xdd, 50);
    hmac_sha256(key, 20, msg, 50, d);
    CHECK(digest_is(d, "773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe"), "test case 3");
    for (int i = 0; i < 25; i++) key[i] = (uint8_t)(i + 1);
    memset(msg, 0xcd, 50);
    hmac_sha256(key, 25, msg, 50, d);
    CHECK(digest_is(d, "82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b"), "test case 4");
    memset(key, 0xaa, 131);
    const char *m6 = "Test Using Larger Than Block-Size Key - Hash Key First";
    hmac_sha256(key, 131, (const uint8_t *)m6, strlen(m6), d);
    CHECK(digest_is(d, "60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54"),
          "test case 6 (131-byte key, hashed first)");
    const char *m7 = "This is a test using a larger than block-size key and a larger than block-size data. "
                     "The key needs to be hashed before being used by the HMAC algorithm.";
    hmac_sha256(key, 131, (const uint8_t *)m7, strlen(m7), d);
    CHECK(digest_is(d, "9b09ffa71b942fcb27635fbcd5b0e944bfdc63644f0713938a7f51535c3a35e2"), "test case 7");
    hmac_sha256_key hk;
    hmac_sha256_setkey(&hk, key, 131);
    uint8_t d2[32];
    hmac_sha256_mac(&hk, (const uint8_t *)m7, strlen(m7), d2);
    hmac_sha256_mac(&hk, (const uint8_t *)m7, strlen(m7), d);
    CHECK(digest_is(d2, "9b09ffa71b942fcb27635fbcd5b0e944bfdc63644f0713938a7f51535c3a35e2") && memcmp(d, d2, 32) == 0,
          "test case 7 again with the precomputed key state, used twice");
}

static uint8_t KEY[FD_KEY_LEN], OTHER[FD_KEY_LEN];

static void test_device(void) {
    printf("\nThe device's rules\n");
    for (int i = 0; i < FD_KEY_LEN; i++) { KEY[i] = (uint8_t)next(); OTHER[i] = (uint8_t)next(); }
    fd_device d;
    fd_init(&d, KEY);
    d.analog_da[1] = 1580;
    uint8_t req[FD_REQ_LEN], resp[FD_RESP_LEN];
    size_t n;

    fd_build_request(KEY, FD_READ_ANALOG, 1, 0, 1, req);
    int s = fd_handle(&d, req, FD_REQ_LEN, resp, &n);
    uint8_t want[32];
    hmac_sha256(KEY, FD_KEY_LEN, resp, FD_RESP_BODY, want);
    CHECK(s == FD_OK && n == FD_RESP_LEN && ((resp[4] << 8) | resp[5]) == 1580 && equal_ct(want, resp + FD_RESP_BODY, 32),
          "a signed read returns 158.0 A in a reply with a valid tag");

    fd_build_request(KEY, FD_OPERATE, 0, 1, 2, req);
    s = fd_handle(&d, req, FD_REQ_LEN, resp, &n);
    CHECK(s == FD_OK && d.switch_closed[0] == 1, "a signed command closes the tie switch");

    s = fd_handle(&d, req, FD_REQ_LEN, resp, &n);
    CHECK(s == FD_REPLAY && n == FD_RESP_LEN, "the same command sent again is refused as a replay");

    fd_build_request(KEY, FD_OPERATE, 0, 0, 1, req);
    s = fd_handle(&d, req, FD_REQ_LEN, resp, &n);
    CHECK(s == FD_REPLAY && d.switch_closed[0] == 1, "an older counter is refused, and the switch stays closed");

    fd_build_request(OTHER, FD_OPERATE, 0, 0, 100, req);
    s = fd_handle(&d, req, FD_REQ_LEN, resp, &n);
    CHECK(s == FD_BAD_TAG && n == 0 && d.switch_closed[0] == 1, "a command signed with the wrong key gets no reply");

    int all_refused = 1, silent = 1;
    fd_build_request(KEY, FD_OPERATE, 0, 0, 3, req);
    for (int bit = 0; bit < FD_REQ_LEN * 8; bit++) {
        uint8_t t[FD_REQ_LEN];
        memcpy(t, req, sizeof t);
        t[bit / 8] ^= (uint8_t)(1u << (bit % 8));
        s = fd_handle(&d, t, FD_REQ_LEN, resp, &n);
        all_refused &= (s == FD_BAD_TAG);
        silent &= (n == 0);
    }
    CHECK(all_refused && silent && d.switch_closed[0] == 1, "flipping any one of the %d bits of a valid command is caught",
          FD_REQ_LEN * 8);

    int lengths = 1;
    uint8_t longer[FD_REQ_LEN + 8];
    memcpy(longer, req, FD_REQ_LEN);
    memset(longer + FD_REQ_LEN, 0, 8);
    for (size_t len = 0; len <= FD_REQ_LEN + 8; len++)
        if (len != FD_REQ_LEN) lengths &= (fd_handle(&d, longer, len, resp, &n) == FD_BAD_LENGTH && n == 0);
    CHECK(lengths && d.switch_closed[0] == 1, "every frame of the wrong length (0 to 40, 42 to 49 bytes) is refused");

    fd_build_request(KEY, FD_OPERATE, 7, 1, 4, req);
    CHECK(fd_handle(&d, req, FD_REQ_LEN, resp, &n) == FD_BAD_POINT, "a genuine command for a point that doesn't exist is refused");
    fd_build_request(KEY, FD_OPERATE, 0, 9, 5, req);
    CHECK(fd_handle(&d, req, FD_REQ_LEN, resp, &n) == FD_BAD_VALUE && d.switch_closed[0] == 1,
          "a genuine command with a value other than open or close is refused");
    fd_build_request(KEY, 0x2a, 0, 0, 6, req);
    CHECK(fd_handle(&d, req, FD_REQ_LEN, resp, &n) == FD_BAD_FUNCTION, "an unknown function code is refused");
    fd_build_request(KEY, FD_OPERATE, 0, 1, 6, req);
    CHECK(fd_handle(&d, req, FD_REQ_LEN, resp, &n) == FD_REPLAY, "a refused command still uses up its counter");

    fd_build_request(KEY, FD_OPERATE, 0, 0, 0xFFFFFFFFu, req);
    fd_handle(&d, req, FD_REQ_LEN, resp, &n);
    fd_build_request(KEY, FD_OPERATE, 0, 1, 0xFFFFFFFFu, req);
    CHECK(fd_handle(&d, req, FD_REQ_LEN, resp, &n) == FD_REPLAY,
          "after the largest counter nothing more is accepted (the key has to be changed)");
}

static void fuzz(long rounds) {
    printf("\nFuzzing: %ld random and mutated frames\n", rounds);
    fd_device d;
    fd_init(&d, KEY);
    uint8_t valid[FD_REQ_LEN], buf[FD_REQ_LEN + 16], resp[FD_RESP_LEN];
    fd_build_request(KEY, FD_OPERATE, 0, 1, 1, valid);
    long accepted = 0, replied = 0;
    for (long i = 0; i < rounds; i++) {
        size_t len;
        if (i % 2 == 0) {                      /* random bytes, random length */
            len = (size_t)(next() % sizeof buf);
            for (size_t j = 0; j < len; j++) buf[j] = (uint8_t)next();
        } else {                               /* a valid frame with 1 to 8 random bits flipped */
            len = FD_REQ_LEN;
            memcpy(buf, valid, FD_REQ_LEN);
            int flips = 1 + (int)(next() % 8);
            for (int k = 0; k < flips; k++) { uint64_t b = next() % (FD_REQ_LEN * 8); buf[b / 8] ^= (uint8_t)(1u << (b % 8)); }
            if (memcmp(buf, valid, FD_REQ_LEN) == 0) buf[0] ^= 1;   /* flips that cancel out */
        }
        size_t n;
        int s = fd_handle(&d, buf, len, resp, &n);
        accepted += (s == FD_OK);
        replied += (n > 0);
    }
    CHECK(accepted == 0, "accepted: %ld", accepted);
    CHECK(replied == 0, "replies sent to a forger: %ld", replied);
}

static void timing(void) {
    printf("\nSpeed on this machine\n");
    static uint8_t mb[1 << 20];
    for (size_t i = 0; i < sizeof mb; i++) mb[i] = (uint8_t)i;
    uint8_t d[32];
    double t0 = now();
    for (int i = 0; i < 64; i++) sha256(mb, sizeof mb, d);
    double t = now() - t0;
    printf("  SHA-256: %.0f MB/s\n", 64 / t);

    /* One tag over a 9-byte request body, computed both ways. */
    uint8_t body[FD_REQ_BODY] = {1, 1, 0, 1, 0, 0, 0, 0, 1}, tag[32];
    hmac_sha256_key hk;
    hmac_sha256_setkey(&hk, KEY, FD_KEY_LEN);
    int reps = 1000000;
    t0 = now();
    for (int i = 0; i < reps; i++) { body[8] = (uint8_t)i; hmac_sha256(KEY, FD_KEY_LEN, body, sizeof body, tag); }
    double plain = (now() - t0) / reps;
    t0 = now();
    for (int i = 0; i < reps; i++) { body[8] = (uint8_t)i; hmac_sha256_mac(&hk, body, sizeof body, tag); }
    double pre = (now() - t0) / reps;
    printf("  one tag, key hashed every time:   %.0f ns (4 compressions)\n", 1e9 * plain);
    printf("  one tag, key state precomputed:   %.0f ns (2 compressions), %.2fx faster\n", 1e9 * pre, plain / pre);

    fd_device dev;
    fd_init(&dev, KEY);
    uint8_t req[FD_REQ_LEN], resp[FD_RESP_LEN];
    size_t n;
    int frames = 200000;
    t0 = now();
    for (int i = 1; i <= frames; i++) {
        fd_build_request(KEY, FD_READ_ANALOG, 1, 0, (uint32_t)(frames + i), req);
        fd_handle(&dev, req, FD_REQ_LEN, resp, &n);
    }
    double both = (now() - t0) / frames;
    printf("  control center signs + device checks and signs its reply: %.2f microseconds per command\n", 1e6 * both);
}

int main(int argc, char **argv) {
    long rounds = argc > 1 ? atol(argv[1]) : 1000000;
    int notime = argc > 2 && strcmp(argv[2], "notime") == 0;   /* sanitizer builds: timings mean nothing */
    test_sha256();
    test_hmac();
    test_device();
    fuzz(rounds);
    if (!notime) timing();
    printf("\n%s: %d failure(s)\n", failures ? "FAIL" : "PASS", failures);
    return failures != 0;
}
