# Threadfin Configuration Bootstrap

## Overview
This Threadfin deployment uses ConfigMaps to bootstrap configuration files for GitOps compatibility. The configuration includes channel mappings, filters, and source configurations extracted from a working Threadfin instance.

## How It Works

### 1. ConfigMaps
- **`threadfin-bootstrap-config`**: Core configuration files (settings.json, urls.json, etc.)
- **`threadfin-xepg-data`**: Large channel database file (xepg.json, ~350KB)

### 2. Init Container Bootstrap
The deployment uses an init container that:
1. Copies configuration files from ConfigMaps to the PVC
2. Ensures proper directory structure
3. Logs bootstrap completion

### 3. Files Included

#### Core Configuration (`configmap-bootstrap.yaml`):
- **`settings.json`**: Main application settings with Russia filter, EPG sources, and streaming config
- **`urls.json`**: ⭐ **Channel mappings** - Contains the manually mapped channels:
  - Звезда Плюс → Channel 1100
  - НТВ → Channel 1163
- **`authentication.json`**: User management (empty - no auth configured)

#### Channel Database (`kustomization.yaml` configMapGenerator):
- **`xepg.json`**: Complete channel database with 11,427 streams, metadata, and EPG mappings

## Configuration Details

### Preserved Settings:
- ✅ API enabled
- ✅ Non-ASCII characters enabled
- ✅ XEPG as EPG source
- ✅ Russia group filter (starting channel 1000)
- ✅ 2 manually mapped channels
- ✅ M3U source: `https://iptv-org.github.io/iptv/index.country.m3u`
- ✅ XMLTV source: `https://iptvx.one/EPG_NOARCH`
- ✅ EPG categories and colors
- ✅ Streaming and buffer settings

### Expected Outcome:
After deployment, Threadfin should have:
- 283 active filtered channels (Russia group)
- 2 mapped channels: 1100 (Звезда Плюс) and 1163 (НТВ)
- Identical M3U output to the original configuration
- All UI settings preserved

## Deployment Process

1. **ConfigMaps Created**: Kustomize generates ConfigMaps from files
2. **Init Container Runs**: Copies files from ConfigMaps to PVC `/home/threadfin/conf/`
3. **Main Container Starts**: Threadfin loads configuration and generates M3U/XMLTV
4. **API Available**: Ready for additional configuration via UI

## Verification

After deployment, verify:
```bash
# Check M3U output contains mapped channels
curl -s https://threadfin.soyspray.vip/m3u/threadfin.m3u | grep -E "(1100|1163)"

# Check API status
curl -s -X POST -H "Content-Type: application/json" -d '{"cmd":"status"}' https://threadfin.soyspray.vip/api/

# Check active streams count (should be 283)
```

## Benefits

### GitOps Compliance:
- ✅ All configuration version controlled
- ✅ Reproducible deployments
- ✅ No manual setup required
- ✅ Channel mappings preserved

### Operational:
- ✅ Fresh deployments have working config
- ✅ PVC allows runtime changes
- ✅ Hybrid approach: GitOps base + UI flexibility
- ✅ No data loss on pod restarts
