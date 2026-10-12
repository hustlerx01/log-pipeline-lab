"""Seeded synthetic logs with known incidents. Writes nginx access, app JSON and auth.log.
Incidents: (a) 5xx burst on /api/checkout, (b) SSH brute force from 203.0.113.50, (c) slow /api/search."""
import argparse, json, random, datetime as dt
from pathlib import Path

def main(out: Path, n: int = 2000, seed: int = 7, now: dt.datetime | None = None):
    rnd = random.Random(seed); out.mkdir(parents=True, exist_ok=True)
    now = now or dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(minutes=10)
    paths = ["/", "/api/products", "/api/search", "/api/checkout", "/healthz", "/static/app.js"]
    truth = {"nginx_5xx": 0, "nginx_total": 0, "healthz": 0, "ssh_failed_bruteforce_ip": 0, "slow_search": 0, "app_errors": 0}
    with open(out / "access.log", "w") as a, open(out / "app.log", "w") as j, open(out / "auth.log", "w") as s:
        for i in range(n):
            t = start + dt.timedelta(seconds=i * 600 / n)
            burst = 0.7 < i / n < 0.8
            p = rnd.choice(paths)
            status = 200
            # upstream DB outage during burst hits all API routes
            if p.startswith("/api/") and burst and rnd.random() < 0.6: status = rnd.choice([500, 502, 503])
            elif rnd.random() < 0.01: status = 404
            rt = rnd.uniform(0.005, 0.12)
            if p == "/api/search" and 0.4 < i / n < 0.5: rt = rnd.uniform(1.5, 3.0); truth["slow_search"] += 1
            ip = f"198.51.100.{rnd.randint(1, 60)}"
            a.write(f'{ip} - - [{t.strftime("%d/%b/%Y:%H:%M:%S +0000")}] "GET {p} HTTP/1.1" {status} {rnd.randint(200, 9000)} "-" "Mozilla/5.0" {rt:.3f}\n')
            truth["nginx_total"] += 1; truth["nginx_5xx"] += status >= 500; truth["healthz"] += p == "/healthz"
            lvl = "error" if status >= 500 else rnd.choice(["info"] * 9 + ["warn"])
            truth["app_errors"] += lvl == "error"
            j.write(json.dumps({"ts": t.isoformat(), "level": lvl, "service": p.split("/")[2] if p.startswith("/api/") else "web",
                                "msg": "upstream payment timeout" if lvl == "error" else "request handled", "path": p, "latency_ms": int(rt * 1000)}) + "\n")
            if i % 10 == 0:
                st = t.strftime("%b %d %H:%M:%S").replace(" 0", "  ", 1) if t.day < 10 else t.strftime("%b %d %H:%M:%S")
                if 0.2 < i / n < 0.3:
                    s.write(f"{st} web-01 sshd[{4000+i}]: Failed password for invalid user admin from 203.0.113.50 port {40000+i} ssh2\n")
                    truth["ssh_failed_bruteforce_ip"] += 1
                else:
                    s.write(f"{st} web-01 sshd[{4000+i}]: Accepted publickey for deploy from 10.0.0.5 port {50000+i} ssh2\n")
    (out / "truth.json").write_text(json.dumps(truth, indent=1))
    return truth

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="logs"); ap.add_argument("-n", type=int, default=2000)
    a = ap.parse_args(); print(json.dumps(main(Path(a.out), a.n)))
