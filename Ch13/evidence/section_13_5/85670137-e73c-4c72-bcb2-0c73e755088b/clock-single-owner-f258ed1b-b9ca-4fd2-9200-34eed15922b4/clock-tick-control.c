/* Own bounded comparison helper. The ONLY write mode is ADJ_TICK. */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/timex.h>
#include <unistd.h>

static void identity(char *boot,size_t size) {
    FILE *f=fopen("/proc/sys/kernel/random/boot_id","r");
    if (!f || !fgets(boot,(int)size,f)) {perror("boot identity");exit(1);}
    fclose(f);boot[strcspn(boot,"\n")]=0;
}
int main(int argc,char **argv) {
    char boot[80],space[80];identity(boot,sizeof boot);
    ssize_t count=readlink("/proc/self/ns/time",space,sizeof(space)-1);
    if(count<0){perror("time namespace");return 1;}space[count]=0;
    struct timex before={0};int read_state=adjtimex(&before);
    if(read_state<0){perror("read adjtimex");return 1;}
    int writing=argc==5 && !strcmp(argv[1],"set-tick");
    if(!(argc==2 && !strcmp(argv[1],"read")) && !writing){fprintf(stderr,"unsupported command\n");return 2;}
    unsigned int write_modes=0;
    if(writing){
        long expected=strtol(argv[2],NULL,10),target=strtol(argv[3],NULL,10);
        if(geteuid()!=0 || strcmp(boot,argv[4]) || sysconf(_SC_CLK_TCK)!=100
           || before.tick!=expected
           || !((expected==9166 && target==10000)||(expected==10000 && target==9166))){
            fprintf(stderr,"tick ownership/identity/approved pair check failed; no write\n");return 3;
        }
        struct timex change={0};change.modes=ADJ_TICK;change.tick=target;
        write_modes=change.modes;
        if(adjtimex(&change)<0){perror("approved ADJ_TICK");return 1;}
    }
    struct timex after={0};if(adjtimex(&after)<0){perror("read after");return 1;}
    printf("{\"boot_id\":\"%s\",\"time_namespace\":\"%s\",\"uid\":%d,\"clock_ticks\":%ld,\"tick_us\":%ld,\"freq_scaled_ppm\":%ld,\"status\":%d,\"before_tick_us\":%ld,\"write_modes\":%u,\"read_state\":%d}\n",boot,space,geteuid(),sysconf(_SC_CLK_TCK),after.tick,after.freq,after.status,before.tick,write_modes,read_state);
    return fflush(stdout)!=0;
}
