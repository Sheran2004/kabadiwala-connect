"""Tiny in-memory limiter (fine for one server process; use Redis if you run several)."""
import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request

class Limiter:
    def __init__(self, n, window): self.n, self.w, self.h = n, window, defaultdict(deque)
    def _q(self, k):
        q, now = self.h[k], time.time()
        while q and now - q[0] > self.w: q.popleft()
        return q
    def check(self, k):
        q = self._q(k)
        if len(q) >= self.n: raise HTTPException(429, f"Too many attempts. Try again in {int(self.w - (time.time() - q[0])) // 60 + 1} minute(s).")
    def hit(self, k): self._q(k).append(time.time())
    def reset(self, k): self.h.pop(k, None)

by_phone = Limiter(5, 900)    # 5 wrong passwords per phone / 15 min
by_ip = Limiter(30, 900)      # 30 wrong passwords per IP / 15 min
def client_ip(r: Request): return (r.headers.get("x-forwarded-for", "").split(",")[0].strip() or (r.client.host if r.client else "?"))
