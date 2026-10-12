#!/usr/bin/env bash
# generate logs -> Fluent Bit (parse/filter/enrich) -> Loki + file archive -> run LogQL alert queries
set -u; cd "$(dirname "$0")/.."; PY=${PYTHON:-python3}
FB=${FB:-$(command -v fluent-bit || echo /opt/fluent-bit/bin/fluent-bit)}
export LOG_DIR=$(mktemp -d) STATE_DIR=$(mktemp -d) LOKI_HOST=127.0.0.1 LOKI_PORT=3100 FB_HTTP_PORT=2020
rm -rf /tmp/loki-lab
loki -config.file=loki/loki.yml > $STATE_DIR/loki.log 2>&1 & L=$!
trap 'kill $L $F 2>/dev/null; pkill -f "fluent-bit.conf" 2>/dev/null' EXIT
for i in $(seq 60); do curl -sf 127.0.0.1:3100/ready >/dev/null && break; sleep 1; done
$PY gen/generate_logs.py --out $LOG_DIR > /dev/null
(cd fluent-bit && exec $FB -c fluent-bit.conf > $STATE_DIR/fb.log 2>&1) & F=$!
sleep ${WAIT:-15}
mkdir -p results; cp $LOG_DIR/truth.json results/truth.json
curl -s 127.0.0.1:2020/api/v1/metrics > results/fluentbit_metrics.json
head -c 1500 $STATE_DIR/archive.jsonl > results/archive_sample.jsonl
$PY scripts/verify.py results/truth.json | tee results/verify.txt
curl -s 127.0.0.1:3100/prometheus/api/v1/rules > results/loki_rules.json
grep -iE "error|fail" $STATE_DIR/fb.log | head -5
