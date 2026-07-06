#!/usr/bin/env bash
set -euo pipefail

expected="banklab-kong-smoke-ok"
external_host="${KONG_SMOKE_EXTERNAL_HOST:-kong-smoke.external.banklab.test}"
internal_host="${KONG_SMOKE_INTERNAL_HOST:-kong-smoke.internal.banklab.test}"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required for Kong route smoke checks." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required for Kong route smoke checks." >&2
  exit 1
fi

proxy_ip="$(kubectl -n platform-kong get service banklab-kong-gateway-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)"

if [[ -n "${proxy_ip}" ]]; then
  curl --fail --silent --show-error --resolve "${external_host}:80:${proxy_ip}" "http://${external_host}/" | grep -F "${expected}"
  curl --fail --silent --show-error --resolve "${internal_host}:80:${proxy_ip}" "http://${internal_host}/" | grep -F "${expected}"
  exit 0
fi

echo "No LoadBalancer IP found. Falling back to kubectl port-forward on localhost:18080." >&2
kubectl -n platform-kong port-forward service/banklab-kong-gateway-proxy 18080:80 >/tmp/banklab-kong-port-forward.log 2>&1 &
pf_pid="$!"
trap 'kill "${pf_pid}" >/dev/null 2>&1 || true' EXIT
sleep 3
curl --fail --silent --show-error -H "Host: ${external_host}" http://127.0.0.1:18080/ | grep -F "${expected}"
curl --fail --silent --show-error -H "Host: ${internal_host}" http://127.0.0.1:18080/ | grep -F "${expected}"
