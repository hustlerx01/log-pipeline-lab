"""Query Loki: compare ingested counts with generator ground truth; run alert expressions as instant queries."""
import json, sys, time, urllib.parse, urllib.request
import yaml
L = "http://127.0.0.1:3100"
NOW = int(time.time())
def q(expr, at=None):
    url = f"{L}/loki/api/v1/query?" + urllib.parse.urlencode({"query": expr, "time": str(at or NOW)})
    return json.load(urllib.request.urlopen(url))["data"]["result"]
def total(expr):
    r = q(expr); return sum(float(x["value"][1]) for x in r), r

truth = json.load(open(sys.argv[1])); rows = []; ok = True
checks = [("nginx lines (healthz dropped)", 'sum(count_over_time({job="nginx"}[15m]))', truth["nginx_total"] - truth["healthz"]),
          ("nginx 5xx", 'sum(count_over_time({job="nginx",status_class="5xx"}[15m]))', truth["nginx_5xx"]),
          ("sshd brute-force lines", 'sum(count_over_time({job="auth",ssh_event="Failed password"}[15m]))', truth["ssh_failed_bruteforce_ip"]),
          ("app error lines", 'sum(count_over_time({job="app",level="error"}[15m]))', truth["app_errors"]),
          ("slow search (>1s)", 'sum(count_over_time({job="nginx"} | json | request_time > 1 [15m]))', truth["slow_search"])]
print("== ingestion vs ground truth ==")
for name, expr, want in checks:
    got, _ = total(expr); good = int(got) == want; ok &= good
    print(f"{'PASS' if good else 'FAIL'}  {name:32} loki={int(got):5}  truth={want}")
print("\n== alert rules evaluated as instant queries at end of run (real 5m windows; the 5xx burst is 2-3 min before end) ==")
for g in yaml.safe_load(open("loki/rules/fake/alerts.yml"))["groups"]:
    for r in g["rules"]:
        expr = r["expr"]
        res = q(expr)
        firing = [(x["metric"], round(float(x["value"][1]), 3)) for x in res]
        print(f"{r['alert']:18} {'FIRING' if firing else 'ok':7} {firing}")
print("\n== backtest: rule condition true at minute T-k (window 5m), k=0..10 ==")
for g in yaml.safe_load(open("loki/rules/fake/alerts.yml"))["groups"]:
    for r in g["rules"]:
        marks = "".join("#" if q(r["expr"], NOW - 60 * k) else "." for k in range(10, -1, -1))
        print(f"{r['alert']:18} T-10 {marks} T-0")
sys.exit(0 if ok else 1)
