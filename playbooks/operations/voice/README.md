# Bounded GI stalled-stream test

This operation pauses only the current GI Python process for four to seven
minutes. Kubernetes TCP probes can still succeed while its reader stops. The
purpose is to verify the actual ingress-stall alert and its Telegram delivery,
then verify recovery after the process resumes. It changes no workload,
image, model, data, credentials, PVC or node configuration.

The operator must explicitly authorize temporary voice disruption. Run from
clean delivered `main` only, with native applications and storage healthy:

```bash
source soyspray-venv/bin/activate
ansible-playbook -i inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu \
  playbooks/operations/voice/test-stalled-stream.yml \
  -e temporary_voice_disruption=true -e voice_test_seconds=360 \
  -e "voice_test_id=$(date -u +%Y%m%dT%H%M%SZ)-$(git rev-parse --short HEAD)"
```

The controller selects one Ready GI pod and its exact container. The host
verifies the Python command and process birth identity. Before SIGSTOP, the
helper arms and verifies an independent systemd SIGCONT timer. Its exit trap
also restores the same process; both paths refuse a reused PID. The operation
runs outside SSH and reports scoped journal timestamps. An identity change or
missing restoration evidence stops the operation; do not improvise repairs.

Before pausing, confirm expected listening, fresh microphone callbacks, run
acknowledgement and GI ingress. During the pause, verify that the device stays
healthy, GI ingress eventually falls, and VoiceAudioStalled fires. Check the
native Alertmanager notification counter and failure counter. Close the old
listening session with Recover GI listening near the end of the test if needed;
observe actual audio flow after automatic SIGCONT and run a real spoken command.
Preserve only timestamps, states, counters, event types and TCP queue sizes.
Never capture audio payloads or transcripts.

`tests/test_gi_pause.py` checks changed-process refusal, a matching-process
restore, and failure to arm restoration before any pause. The existing network
operation tests protect Ethernet restoration and do not own process signals.
The live journal verifies that restoration was armed before the actual pause.
