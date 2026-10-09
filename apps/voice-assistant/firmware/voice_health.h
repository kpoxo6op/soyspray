#pragma once

#include <atomic>
#include <cstdint>

namespace gi {

enum class Action { NONE, RETRY, REBOOT, EXHAUSTED };
enum class Reason : uint32_t { NONE, NOT_RUNNING, NO_ACK, MIC_STALE, STOP_TIMEOUT, BUSY_TIMEOUT, MANUAL };

struct Input {
  uint32_t now;
  bool connected;
  bool muted;
  bool ota;
  bool running;
  bool acknowledged;
  // 0: waiting, 1: interaction, 2: announcement/timer.
  uint32_t busy;
  uint32_t reboot_count;
};

// Owns timeouts and recovery policy, independent of ESPHome and the audio content.
class Supervisor {
 public:
  std::atomic<uint32_t> last_frame{0};
  std::atomic<bool> frame_seen{false};
  Reason reason{Reason::NONE};
  bool expected{false};
  bool reset_budget{false};
  uint32_t retries{0};

  static uint32_t elapsed(uint32_t now, uint32_t then) { return now - then; }

  void frame(uint32_t now) {
    last_frame.store(now, std::memory_order_relaxed);
    frame_seen.store(true, std::memory_order_relaxed);
  }
  uint32_t frame_age(uint32_t now) const {
    return frame_seen.load(std::memory_order_relaxed)
               ? elapsed(now, last_frame.load(std::memory_order_relaxed))
               : UINT32_MAX;
  }
  void backend_error(uint32_t now) { backend_seen_ = true; backend_at_ = now; }
  void new_run(uint32_t now) { expectation_at_ = now; healthy_ = false; stop_failed_ = false; }
  void stop_failed() { stop_failed_ = true; }

  Action tick(const Input &in) {
    reset_budget = false;
    expected = false;
    if (!boot_seen_) { boot_seen_ = true; boot_at_ = in.now; }
    boot_ready_ = boot_ready_ || elapsed(in.now, boot_at_) >= 180000;
    if (!in.connected) {
      connected_ = false;
      connected_ready_ = false;
      clear_wait_(in.now);
      return Action::NONE;
    }
    if (!connected_) { connected_ = true; connected_at_ = in.now; }
    connected_ready_ = connected_ready_ || elapsed(in.now, connected_at_) >= 45000;
    if (!boot_ready_ || !connected_ready_ || in.muted || in.ota ||
        (backend_seen_ && elapsed(in.now, backend_at_) < 60000)) {
      clear_wait_(in.now);
      return Action::NONE;
    }
    if (in.busy != busy_) { busy_ = in.busy; busy_at_ = in.now; }
    bool busy_expired = in.busy && elapsed(in.now, busy_at_) >= (in.busy == 1 ? 120000U : 900000U);
    if (in.busy && !busy_expired) { clear_wait_(in.now); return Action::NONE; }
    if (!was_expected_) { was_expected_ = true; expectation_at_ = in.now; }
    expected = true;
    bool fresh = frame_age(in.now) <= 5000;
    bool good = in.running && in.acknowledged && fresh && !busy_expired && !stop_failed_;
    if (good) {
      fault_seen_ = false;
      retries = 0;
      if (!healthy_) { healthy_ = true; healthy_at_ = in.now; }
      reset_budget = elapsed(in.now, healthy_at_) >= 1800000;
      return Action::NONE;
    }
    healthy_ = false;
    Reason fault = Reason::NONE;
    if (stop_failed_) fault = Reason::STOP_TIMEOUT;
    else if (busy_expired) fault = Reason::BUSY_TIMEOUT;
    else if (!in.running) fault = Reason::NOT_RUNNING;
    else if (!in.acknowledged && elapsed(in.now, expectation_at_) >= 20000) fault = Reason::NO_ACK;
    else if (in.acknowledged && !fresh) fault = Reason::MIC_STALE;
    if (fault == Reason::NONE) return Action::NONE;
    if (in.reboot_count >= 3) { reason = fault; return Action::EXHAUSTED; }
    if (!fault_seen_) { fault_seen_ = true; fault_at_ = in.now; }
    if (fault == Reason::NOT_RUNNING && elapsed(in.now, fault_at_) < 15000) return Action::NONE;
    if (retries && elapsed(in.now, attempt_at_) < 30000 && !stop_failed_) return Action::NONE;
    reason = fault;
    attempt_at_ = in.now;
    if (stop_failed_ || retries >= 2) {
      stop_failed_ = false;
      return in.reboot_count < 3 ? Action::REBOOT : Action::EXHAUSTED;
    }
    ++retries;
    expectation_at_ = in.now;
    return Action::RETRY;
  }

 private:
  bool boot_seen_{false}, boot_ready_{false}, connected_{false}, connected_ready_{false}, backend_seen_{false};
  bool was_expected_{false}, healthy_{false}, fault_seen_{false}, stop_failed_{false};
  uint32_t boot_at_{0}, connected_at_{0}, backend_at_{0}, expectation_at_{0};
  uint32_t busy_{0}, busy_at_{0}, healthy_at_{0}, fault_at_{0}, attempt_at_{0};
  void clear_wait_(uint32_t now) {
    was_expected_ = false;
    healthy_ = false;
    fault_seen_ = false;
    expectation_at_ = now;
  }
};

inline Supervisor &supervisor() {
  static Supervisor instance;
  return instance;
}

}  // namespace gi
