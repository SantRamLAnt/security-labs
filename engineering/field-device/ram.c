/* Not part of the device: an array the size of the device's state, so the cross build can report
 * how much RAM the state takes on the Cortex-M0+ itself (where pointers and size_t are 4 bytes). */
#include "device.h"
char fd_device_ram_bytes[sizeof(fd_device)];
