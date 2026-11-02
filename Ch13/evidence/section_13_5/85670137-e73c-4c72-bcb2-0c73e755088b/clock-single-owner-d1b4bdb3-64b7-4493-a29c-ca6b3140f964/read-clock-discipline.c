/* Ch13 diagnostic only. adjtimex modes=0 is read-only; never set a clock. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdio.h>
#include <sys/timex.h>
#include <time.h>
#include <unistd.h>

static long long ns(clockid_t id) {
    struct timespec value;
    if (clock_gettime(id, &value)) { perror("clock_gettime"); _exit(1); }
    return (long long)value.tv_sec * 1000000000LL + value.tv_nsec;
}
int main(void) {
    const long long start = ns(CLOCK_MONOTONIC_RAW);
    struct timespec pause = {.tv_sec=0, .tv_nsec=20000000};
    printf("{\"kind\":\"metadata\",\"uid\":%d,\"pid\":%d,\"adjtimex_modes\":0,\"writes_system_settings\":false,\"raw_duration_ns\":150000000000}\n",getuid(),getpid());
    while (ns(CLOCK_MONOTONIC_RAW) - start < 150000000000LL) {
        long long before=ns(CLOCK_MONOTONIC_RAW);
        long long realtime=ns(CLOCK_REALTIME),monotonic=ns(CLOCK_MONOTONIC);
        struct timex state = {0};
        errno=0; int result=adjtimex(&state),error=errno;
        long long after=ns(CLOCK_MONOTONIC_RAW);
        if (result<0) { perror("read-only adjtimex"); return 1; }
        printf("{\"raw_before_ns\":%lld,\"realtime_ns\":%lld,\"monotonic_ns\":%lld,\"raw_after_ns\":%lld,\"modes\":%u,\"state\":%d,\"errno\":%d,\"tick_us\":%ld,\"freq_scaled_ppm\":%ld,\"status\":%d,\"offset\":%ld,\"constant\":%ld}\n",before,realtime,monotonic,after,state.modes,result,error,state.tick,state.freq,state.status,state.offset,state.constant);
        if (fflush(stdout)) return 1;
        nanosleep(&pause,0);
    }
    printf("{\"kind\":\"finished\",\"raw_elapsed_ns\":%lld,\"writes_system_settings\":false}\n",ns(CLOCK_MONOTONIC_RAW)-start);
    return fflush(stdout)!=0;
}
