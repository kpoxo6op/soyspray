# Calibre Web

Minimal MVP deployment of Calibre Web under the 'media' namespace

Access the UI at <http://192.168.1.132:8083>

## Smoke-test routine

```sh
argocd app sync calibre-web
kubectl logs -n media job/calibre-web-import -f
kubectl exec -n media deploy/calibre-web -- \
  sqlite3 /config/app.db "SELECT name,role FROM user;"
# → Guest|290
kubectl exec -n media deploy/calibre-web -- \
  sqlite3 /config/app.db "SELECT config_anonbrowse FROM settings;"
# → 1
kubectl exec -n media deploy/calibre-web -- \
  sqlite3 /config/app.db "SELECT config_calibre_dir FROM settings;"
# expected → /books/Calibre_Library
```
