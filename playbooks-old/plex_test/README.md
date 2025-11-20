# Plex Test Playbooks

Bare-metal Plex Media Server testing suite for remote functionality outside Kubernetes.

## Usage

```bash
# Activate virtual environment
source soyspray-venv/bin/activate

# Install Plex
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/plex_test/install-plex.yml --tags plex -l kube_node[0]

# Check status
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/plex_test/check-plex.yml --tags plex -l kube_node[0]

# Remove Plex (idempotent)
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/plex_test/remove-plex.yml --tags plex -l kube_node[0]
```

## Post-Installation

1. Open `http://<server-ip>:32400/web`
2. Sign in and claim server

### Claim via API (Recommended)

```bash
# Get your claim token from: https://plex.tv/claim
CLAIM_TOKEN='claim-bWb9pyV2XNC5EEowJ7aU'

# Get server identifiers
CLIENT_ID=$(curl -s http://127.0.0.1:32400/identity | grep -oP 'machineIdentifier="\K[^"]+')
VERSION=$(dpkg-query -W -f='${Version}' plexmediaserver 2>/dev/null)

# Claim the server
curl -s -X POST "http://127.0.0.1:32400/myplex/claim?token=$CLAIM_TOKEN" \
  -H "X-Plex-Product=PlexMediaServer" \
  -H "X-Plex-Version:$VERSION" \
  -H "X-Plex-Client-Identifier:$CLIENT_ID" \
  -H "X-Plex-Platform:Linux"

# Verify claim succeeded
curl -s http://127.0.0.1:32400/identity | grep claimed
# Should show: claimed="1"
```

### Add Demo Library

Create a demo library with sample videos:

```bash
# Create demo videos directory
sudo mkdir -p /var/lib/plexmediaserver/other-videos

# Download sample video files
sudo curl -L --fail --progress-bar \
  https://download.samplelib.com/mp4/sample-5s.mp4 \
  -o /var/lib/plexmediaserver/other-videos/sample-5s.mp4

sudo curl -L --fail --progress-bar \
  https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4 \
  -o /var/lib/plexmediaserver/other-videos/Big_Buck_Bunny_10s_1MB.mp4

# Set proper permissions
sudo chown -R plex:plex /var/lib/plexmediaserver/other-videos

# Verify files downloaded
ls -la /var/lib/plexmediaserver/other-videos/
```

3. Enable Remote Access in Settings
4. Add media library pointing to `/var/lib/plexmediaserver/other-videos`
5. Test remote playback at app.plex.tv

## ✅ Minimal Setup Success

**This setup works flawlessly for remote play with zero additional configuration:**

- ✅ **No firewall configuration needed**
- ✅ **No Plex settings changes required**
- ✅ **No port mappings or forwarding**
- ✅ **No router configuration**
- ✅ **No manual network setup**

After claiming the server and creating a demo library, remote access works immediately via Plex Relay. The server automatically handles all networking and connectivity.

## Files

- `install-plex.yml` - Install from official APT repo
- `remove-plex.yml` - Complete removal (safe to run multiple times)

## Variables

- `plex_port`: 32400
- `plex_service`: plexmediaserver
- `plex_user`: plex
