#include "voice_health.h"
#include <cassert>
#include <string>

using gi::Action;

int main(int argc, char **argv) {
  assert(argc == 2);
  std::string scenario(argv[1]);
  gi::Supervisor policy;
  gi::Input in{1000, true, false, false, true, true, 0, 0};
  policy.frame(in.now);
  assert(policy.tick(in) == Action::NONE);
  in.now += 181000;
  policy.frame(in.now);
  assert(policy.tick(in) == Action::NONE);
  assert(policy.expected);
  if (scenario == "quiet") {
    for (int second = 0; second < 3600; ++second) {
      in.now += 1000;
      policy.frame(in.now); // Nonempty silence is progress too.
      assert(policy.tick(in) == Action::NONE);
    }
    assert(policy.reset_budget);
  } else if (scenario == "guards") {
    in.running = false;
    in.acknowledged = false;
    for (int guard = 0; guard < 5; ++guard) {
      in.connected = guard != 0;
      in.muted = guard == 1;
      in.ota = guard == 2;
      in.busy = guard == 3 ? 2 : 0;
      if (guard == 4) policy.backend_error(in.now);
      for (int second = 0; second < 50; ++second) {
        in.now += 1000;
        assert(policy.tick(in) == Action::NONE);
        assert(!policy.expected);
      }
    }
  } else if (scenario == "idle") {
    in.running = false;
    assert(policy.tick(in) == Action::NONE);
    in.now += 15000;
    assert(policy.tick(in) == Action::RETRY);
    assert(policy.reason == gi::Reason::NOT_RUNNING);
  } else if (scenario == "no_ack") {
    in.acknowledged = false;
    in.now += 19000;
    policy.frame(in.now);
    assert(policy.tick(in) == Action::NONE);
    in.now += 1000;
    policy.frame(in.now);
    assert(policy.tick(in) == Action::RETRY);
    assert(policy.reason == gi::Reason::NO_ACK);
  } else if (scenario == "stale") {
    in.now += 5001;
    assert(policy.tick(in) == Action::RETRY);
    assert(policy.reason == gi::Reason::MIC_STALE);
    in.now += 1000;
    policy.frame(in.now);
    assert(policy.tick(in) == Action::NONE);
  } else if (scenario == "budget") {
    in.now += 6000;
    assert(policy.tick(in) == Action::RETRY);
    in.now += 29999;
    assert(policy.tick(in) == Action::NONE);
    in.now += 1;
    assert(policy.tick(in) == Action::RETRY);
    in.now += 30000;
    assert(policy.tick(in) == Action::REBOOT);
    in.reboot_count = 3;
    in.now += 30000;
    assert(policy.tick(in) == Action::EXHAUSTED);
  } else if (scenario == "wrap") {
    in.now = UINT32_MAX - 2000;
    policy.frame(in.now);
    assert(policy.tick(in) == Action::NONE);
    in.now += 5001;
    assert(policy.tick(in) == Action::RETRY);
    assert(policy.reason == gi::Reason::MIC_STALE);
  } else if (scenario == "busy_cap") {
    in.busy = 1;
    assert(policy.tick(in) == Action::NONE);
    in.now += 119999;
    assert(policy.tick(in) == Action::NONE);
    in.now += 1;
    assert(policy.tick(in) == Action::RETRY);
    assert(policy.reason == gi::Reason::BUSY_TIMEOUT);
  } else if (scenario == "stop_timeout") {
    policy.stop_failed();
    assert(policy.tick(in) == Action::REBOOT);
    assert(policy.reason == gi::Reason::STOP_TIMEOUT);
    in.reboot_count = 3;
    assert(policy.tick(in) == Action::NONE);
    policy.stop_failed();
    assert(policy.tick(in) == Action::EXHAUSTED);
    assert(policy.tick(in) == Action::EXHAUSTED);
  } else if (scenario == "reconnect") {
    in.connected = false;
    in.running = false;
    in.acknowledged = false;
    assert(policy.tick(in) == Action::NONE);
    in.connected = true;
    assert(policy.tick(in) == Action::NONE);
    in.now += 44999;
    assert(policy.tick(in) == Action::NONE);
    in.now += 1;
    assert(policy.tick(in) == Action::NONE);
    in.now += 15000;
    assert(policy.tick(in) == Action::RETRY);
  } else {
    return 2;
  }
}
