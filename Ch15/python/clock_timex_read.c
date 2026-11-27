/* Linux read-only timex snapshot. modes=0 is a query, not a write. */
#include <stdio.h>
#include <sys/timex.h>
#include <time.h>
int main(void) {
    struct timex tx = {0};
    struct timespec mono = {0};
    clock_gettime(CLOCK_MONOTONIC, &mono);
    int state = adjtimex(&tx);
    if (state < 0) { perror("adjtimex query"); return 1; }
    printf("{\"monotonic_ns\":%lld,\"state\":%d,\"modes\":%u,\"offset\":%ld,\"freq_scaled_ppm\":%ld,\"freq_ppm\":%.9f,\"tick_us\":%ld,\"status\":%d,\"maxerror_us\":%ld,\"esterror_us\":%ld,\"tolerance_scaled_ppm\":%ld}\n", (long long)mono.tv_sec*1000000000LL+mono.tv_nsec,state,tx.modes,tx.offset,tx.freq,tx.freq/65536.0,tx.tick,tx.status,tx.maxerror,tx.esterror,tx.tolerance);
    return 0;
}
