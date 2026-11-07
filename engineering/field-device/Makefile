# Host builds for tests and the simulator; a cross build for the Raspberry Pi Pico's RP2040
# (Arm Cortex-M0+) to measure code size and memory. The cross build needs gcc-arm-none-eabi.
CFLAGS = -std=c11 -Wall -Wextra -Werror -O2 -D_POSIX_C_SOURCE=199309L
SRC = device.c sha256.c

test-asan: test_device.c $(SRC)
	$(CC) $(CFLAGS) -fsanitize=address,undefined -fno-sanitize-recover=all -o $@ $^

test: test_device.c $(SRC)
	$(CC) $(CFLAGS) -o $@ $^

sim: sim.c $(SRC)
	$(CC) $(CFLAGS) -o $@ $^

ARM = arm-none-eabi-gcc -mcpu=cortex-m0plus -mthumb -Os -std=c11 -Wall -Wextra -Werror -ffreestanding -fstack-usage
cross: $(SRC) ram.c
	$(ARM) -c device.c -o device.o
	$(ARM) -c sha256.c -o sha256.o
	$(ARM) -c ram.c -o ram.o

clean:
	rm -f test test-asan sim *.o *.su
