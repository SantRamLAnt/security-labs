/* The device behind a text "serial line": one command per line on stdin, one answer per line on
 * stdout. This is how the Python control center (master.py) talks to the C code in CI, standing
 * in for the UART or network link a real board would use.
 *
 *   KEY <64 hex>          load the shared key
 *   SET <point> <tenths>  the sensor simulation: what analog point <point> now reads
 *   FRAME <hex>           a request; answers REPLY <hex> or SILENT <status>
 *   STATE                 answers STATE <switch> <a0> <a1> <a2> <accepted> <refused>
 *   HASH <hex>            answers DIGEST <hex>      (for cross-checking against Python's hashlib)
 *   HMAC <keyhex> <hex>   answers TAG <hex>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "device.h"

#define MAXLINE 8192

static int unhex(const char *s, uint8_t *out, size_t max, size_t *n) {
    size_t len = strlen(s);
    if (len % 2 || len / 2 > max) return 0;
    for (size_t i = 0; i < len / 2; i++) {
        unsigned v;
        if (sscanf(s + 2 * i, "%2x", &v) != 1) return 0;
        out[i] = (uint8_t)v;
    }
    *n = len / 2;
    return 1;
}

static void puthex(const char *tag, const uint8_t *b, size_t n) {
    printf("%s ", tag);
    for (size_t i = 0; i < n; i++) printf("%02x", b[i]);
    printf("\n");
}

int main(void) {
    static char line[MAXLINE];
    static uint8_t buf[MAXLINE / 2], key[MAXLINE / 2];
    fd_device d;
    uint8_t zero[FD_KEY_LEN] = {0};
    fd_init(&d, zero);
    while (fgets(line, sizeof line, stdin)) {
        line[strcspn(line, "\r\n")] = 0;
        char *cmd = strtok(line, " "), *a = strtok(NULL, " "), *b = strtok(NULL, " ");
        size_t n = 0, kn = 0;
        if (!cmd) continue;
        if (!strcmp(cmd, "KEY") && a && unhex(a, key, FD_KEY_LEN, &kn) && kn == FD_KEY_LEN) {
            fd_init(&d, key);
            printf("OK\n");
        } else if (!strcmp(cmd, "SET") && a && b && atoi(a) >= 0 && atoi(a) < FD_NUM_ANALOG) {
            d.analog_da[atoi(a)] = (uint16_t)atoi(b);
            printf("OK\n");
        } else if (!strcmp(cmd, "FRAME") && a && unhex(a, buf, sizeof buf, &n)) {
            uint8_t resp[FD_RESP_LEN];
            size_t rn;
            int s = fd_handle(&d, buf, n, resp, &rn);
            if (rn) puthex("REPLY", resp, rn);
            else printf("SILENT %d\n", s);
        } else if (!strcmp(cmd, "STATE")) {
            printf("STATE %u %u %u %u %u %u\n", d.switch_closed[0], d.analog_da[0], d.analog_da[1], d.analog_da[2],
                   (unsigned)d.accepted, (unsigned)d.refused);
        } else if (!strcmp(cmd, "HASH") && a && unhex(a[0] == '-' ? "" : a, buf, sizeof buf, &n)) {
            uint8_t dg[32];
            sha256(buf, n, dg);
            puthex("DIGEST", dg, 32);
        } else if (!strcmp(cmd, "HMAC") && a && b && unhex(a[0] == '-' ? "" : a, key, sizeof key, &kn) &&
                   unhex(b[0] == '-' ? "" : b, buf, sizeof buf, &n)) {
            uint8_t tg[32];
            hmac_sha256(key, kn, buf, n, tg);
            puthex("TAG", tg, 32);
        } else if (!strcmp(cmd, "QUIT")) {
            break;
        } else {
            printf("ERR\n");
        }
        fflush(stdout);
    }
    return 0;
}
