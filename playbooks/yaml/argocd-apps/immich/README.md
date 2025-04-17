# Immich Application Configuration

This document outlines the configuration and key troubleshooting steps for the Immich application deployed in Kubernetes.

## Troubleshooting

### Port Configuration

**Critical Issue**: Immich server defaults to port 3001 but the Kubernetes service expects 2283

- **Problem**: The application starts on port 3001 by default, causing startup probe failures with the error:

  ```
  Startup probe failed: Get "http://10.233.70.108:2283/api/server/ping": dial tcp 10.233.70.108:2283: connect: connection refused
  ```

- **Solution**: Set the `IMMICH_PORT` environment variable in the deployment:

  ```yaml
  env:
  - name: IMMICH_PORT
    value: "2283"
  ```

- **Verification**: Check inside the container where the default port is defined:

  ```bash
  # Check the current port setting in the application code
  kubectl exec -it <pod-name> -n immich -- grep -n "3001" /usr/src/app/dist/workers/api.js

  # Output shows the issue:
  # const port = Number(process.env.IMMICH_PORT) || 3001;
  ```

### Environment Variable Debugging

- Check all environment variables in the container:

  ```bash
  kubectl exec -it <pod-name> -n immich -- env | sort
  ```

- Check specific Immich-related variables:

  ```bash
  kubectl exec -it <pod-name> -n immich -- env | grep -i port
  ```

### Pod and Deployment Analysis

- Check pod status and events:

  ```bash
  kubectl describe pod <pod-name> -n immich | grep -A20 Events
  ```

- View container logs:

  ```bash
  kubectl logs <pod-name> -n immich
  ```

- Check if the application is listening on the expected port:

  ```bash
  kubectl exec -it <pod-name> -n immich -- netstat -tulpn | grep LISTEN
  ```

### Verifying Connectivity

- Check immich server inside the cluster:

  ```bash
  kubectl -n immich run curltest --rm -it --image=curlimages/curl --restart=Never -- \
    curl -v http://immich-server.immich.svc.cluster.local:2283/api/server/ping
  ```

  Expect `{"res":"pong"}` as the response.

- Check external HTTP access (should redirect to HTTPS):

  ```bash
  curl -v http://immich.soyspray.vip/api/server/ping
  ```

  Expected response should include: `HTTP/1.1 308 Permanent Redirect` with `Location: https://immich.soyspray.vip/api/server/ping`

- Check external HTTPS access:

  ```bash
  curl -vk https://immich.soyspray.vip/api/server/ping
  ```

  Expected response should include: `HTTP/2 200` with `{"res":"pong"}`

### Verifying TLS Certificate

- Check the TLS certificate details:

  ```bash
  openssl s_client -connect immich.soyspray.vip:443 -servername immich.soyspray.vip </dev/null
  ```

  This should show details of the certificate chain, including issuer (Let's Encrypt), validity dates, and verification result.

Check immich server inside the cluster

```sh
kubectl -n immich run curltest --rm -it --image=curlimages/curl --restart=Never -- \
  curl -v http://immich-server.immich.svc.cluster.local:2283/api/server/ping
```

expect `"{"res":"pong"}"` answer

