# Interview talking points: log-pipeline-lab
1. **Ground truth beats eyeballing.** The generator emits `truth.json`, and verify.py asserts that Loki counts match exactly. That's how you prove there's no silent drop or mis-parse.
2. **Label cardinality.** status_class (5 values) is a label. Status code, path and IP stay in the line and are filtered at query time with `| json`. High-cardinality labels kill Loki.
3. **Edge filtering.** Dropping /healthz removed 17% of nginx lines before storage. Cheapest log is the one you never ship.
4. **Ratio alerts dilute.** A checkout-only outage was 1% of all traffic and never crossed 5%. Alert per route or per SLO (burn rate), not global ratios only.
5. **Backtesting alerts.** Evaluating the rule at T-10…T-0 shows each fires only during its incident, so I can show both no false positives and detection coverage.
6. **Fan-out.** The same records go to Loki (hot) and a JSONL archive (cold, e.g. S3) for compliance retention.
7. **Security tie-in.** The SSH brute-force rule maps to T1110.001. This is the same pipeline a SOC uses; Sigma rules could be translated to LogQL.
