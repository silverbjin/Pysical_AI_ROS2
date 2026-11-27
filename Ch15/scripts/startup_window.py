"""Read-only pre-ARM liveness admission; never reset or bypass native guards."""
class StartupWindow:
    def __init__(self):
        self.begin=None;self.last=None;self.last_advance=None;self.resets=0
    def observe(self, now, stamps, ready):
        # Source stamps must advance. A repeated callback does not refresh liveness.
        if not ready or any(x<=0 for x in stamps):
            self.clear();return False
        if self.last is not None and any(a<b for a,b in zip(stamps,self.last)):
            self.clear();return False
        if self.last is None:
            self.begin=(now,stamps);self.last=stamps;self.last_advance=[now]*len(stamps)
            return False
        # Check the OLD receipt ages before accepting newly advanced stamps.
        # Otherwise a stopped executor could resume with fresh samples and
        # conceal the gap in the continuous admission window.
        if any(now-t>.10 for t in self.last_advance):
            self.clear();return False
        for i,(a,b) in enumerate(zip(stamps,self.last)):
            if a>b:self.last_advance[i]=now
        self.last=stamps
        return now-self.begin[0]>=2.0 and all(a-b>=1_000_000_000 for a,b in zip(stamps,self.begin[1]))
    def clear(self):
        if self.begin is not None:self.resets+=1
        self.begin=self.last=self.last_advance=None
