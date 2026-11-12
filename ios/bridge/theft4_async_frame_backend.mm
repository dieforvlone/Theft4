#include "theft4_async_frame_backend.h"
#include "theft4_retail_mode.h"
#import <Foundation/Foundation.h>
#include <pthread.h>
#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <functional>
#include <map>
#include <mutex>
#include <thread>

namespace theft4::render {
namespace {
using Clock = std::chrono::steady_clock;

class AsyncFrameBackend final : public FrameBackend {
 public:
  AsyncFrameBackend(std::unique_ptr<FrameBackend> backend, void (*diagnostic)(const char*))
      : backend_(std::move(backend)), diagnostic_(diagnostic),
        capabilities_(backend_->Capabilities()), presentation_(backend_->HasPresentation()) {
    thread_ = std::thread([this] { Run(); });
  }
  ~AsyncFrameBackend() override { Close(); }

  // Immutable after construction (see FrameBackend); read without the worker.
  BackendCapabilities Capabilities() const override { return capabilities_; }
  bool HasPresentation() const override { return presentation_; }

  bool Open(std::string& error) override {
    return Call(error, [&](std::string& e) { return backend_->Open(e); });
  }
  bool Target(PresentationTarget& target, std::string& error) override {
    return Call(error, [&](std::string& e) { return backend_->Target(target, e); });
  }
  bool ReadRGBA8(const FramePlan& plan, SurfaceView view, std::vector<uint8_t>& bytes,
                 std::string& error) override {
    return Call(error, [&](std::string& e) { return backend_->ReadRGBA8(plan, view, bytes, e); });
  }
  bool ReadColor(const FramePlan& plan, SurfaceView view, ColorReadback& readback,
                 std::string& error) override {
    return Call(error, [&](std::string& e) { return backend_->ReadColor(plan, view, readback, e); });
  }
  bool Drain(std::string& error) override {
    std::string failure;
    const bool drained = Call(error, [&](std::string& e) { return backend_->Drain(e); }, &failure);
    if (drained && !failure.empty()) { error = failure; return false; }
    return drained;
  }
  void Close() override {
    if (closed_) return;
    closed_ = true;
    std::string ignored;
    Call(ignored, [&](std::string&) { backend_->Close(); return true; });
    {
      std::lock_guard lock(mutex_);
      stopped_ = true;
    }
    wake_.notify_all();
    if (thread_.joinable()) thread_.join();
  }

  bool TakeContentsReset() override {
    const bool reset = contents_reset_;
    contents_reset_ = false;
    return reset;
  }

  bool Submit(std::shared_ptr<const FramePlan> plan, bool present, std::string& error,
              SurfaceContents* published) override {
    if (!plan || synchronous_)
      return Call(error, [&](std::string& e) { return backend_->Submit(plan, present, e, published); });
    const auto began = Clock::now();
    std::unique_lock lock(mutex_);
    if (stopped_) { error = "Metal encoder thread stopped"; return false; }
    idle_.wait(lock, [&] { return !job_; });
    const double waited_ms = std::chrono::duration<double, std::milli>(Clock::now() - began).count();
    if (TakeFailure(error)) return false;  // This frame is dropped; later frames submit synchronously.
    // predicted_ is only used on this (the caller's) thread.
    auto expected = std::make_shared<SurfaceContents>();
    PredictFrameContents(*plan, predicted_, *expected);
    Commit(*plan, *expected);
    job_ = [this, plan, present, expected] {
      std::string e;
      SurfaceContents actual;
      if (!SubmitWithDrawableRetry(plan, present, e, actual))
        failure_ = e.empty() ? "Metal encoder submission failed" : e;
      else if (actual != *expected)
        failure_ = "Metal encoder published contents that differ from the prediction";
    };
    wake_.notify_all();
    lock.unlock();
    if (published) *published = *expected;
    Record(waited_ms);
    error.clear();
    return true;
  }

 private:
  // Runs fn on the worker after queued work and waits for it. A pending
  // asynchronous failure is left for Submit, or handed to `failure`.
  template <class F>
  bool Call(std::string& error, F&& fn, std::string* failure = nullptr) {
    std::unique_lock lock(mutex_);
    if (stopped_) { error = "Metal encoder thread stopped"; return false; }
    idle_.wait(lock, [&] { return !job_; });
    if (failure && !failure_.empty()) TakeFailure(*failure);
    bool result = false;
    job_ = [&] { result = fn(error); };
    wake_.notify_all();
    idle_.wait(lock, [&] { return !job_; });
    return result;
  }

  void Run() {
    pthread_setname_np("Theft4 Metal encoder");
    pthread_set_qos_class_self_np(QOS_CLASS_USER_INITIATED, 0);
    std::unique_lock lock(mutex_);
    for (;;) {
      wake_.wait(lock, [&] { return stopped_ || job_; });
      if (!job_) return;
      // job_ stays set while it runs: callers wait for it to clear.
      lock.unlock();
      @autoreleasepool {
        job_();
      }
      lock.lock();
      job_ = nullptr;
      idle_.notify_all();
    }
  }

  // The drawable can be briefly unavailable. The wrapped backend returns
  // before encoding in that case, so retrying the same frame is safe; the
  // caller has already published its contents and cannot drop it.
  bool SubmitWithDrawableRetry(const std::shared_ptr<const FramePlan>& plan, bool present,
                               std::string& error, SurfaceContents& actual) {
    for (int attempt = 0;; ++attempt) {
      error.clear();
      actual.clear();
      if (backend_->Submit(plan, present, error, &actual)) return true;
      if (!present || attempt >= 100 || error != "Metal drawable temporarily unavailable") return false;
      std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
  }

  // Requires mutex_ held and no job running.
  bool TakeFailure(std::string& error) {
    if (failure_.empty()) return false;
    error = "Asynchronous Metal submission failed: " + failure_;
    failure_.clear();
    synchronous_ = true;
    contents_reset_ = true;
    predicted_.clear();
    owners_.clear();
    Log(("gta4-metal-async: " + error + "; continuing with synchronous submission").c_str());
    return true;
  }

  // Mirror the backend's journal update: each declared surface's contents
  // become exactly what the frame published.
  void Commit(const FramePlan& plan, const SurfaceContents& final) {
    for (const auto& surface : plan.surfaces) {
      if (!surface) continue;
      Forget(surface->key);
      owners_[surface->key] = surface;
    }
    predicted_.insert(final.begin(), final.end());
    if (++commits_ % 120 == 0) {
      for (auto it = owners_.begin(); it != owners_.end();) {
        if (it->second.expired()) { Forget(it->first); it = owners_.erase(it); }
        else ++it;
      }
    }
  }
  void Forget(SurfaceKey key) {
    auto first = predicted_.lower_bound(SurfaceView{key});
    auto last = first;
    while (last != predicted_.end() && last->surface == key) ++last;
    predicted_.erase(first, last);
  }

  void Record(double waited_ms) {
    if (!theft4_renderer_timing()) return;
    wait_total_ms_ += waited_ms;
    wait_max_ms_ = std::max(wait_max_ms_, waited_ms);
    if (++timed_submits_ % 60) return;
    char message[192];
    std::snprintf(message, sizeof(message),
                  "gta4-metal-async: submits=60 caller-wait-avg-ms=%.3f caller-wait-max-ms=%.3f tracked-surfaces=%zu",
                  wait_total_ms_ / 60.0, wait_max_ms_, owners_.size());
    Log(message);
    wait_total_ms_ = wait_max_ms_ = 0;
  }
  void Log(const char* message) {
    if (diagnostic_) diagnostic_(message);
    else std::fprintf(stderr, "%s\n", message);
  }

  std::unique_ptr<FrameBackend> backend_;
  void (*diagnostic_)(const char*);
  const BackendCapabilities capabilities_;
  const bool presentation_;
  std::mutex mutex_;
  std::condition_variable wake_, idle_;
  std::function<void()> job_;
  std::string failure_;
  bool stopped_ = false;
  std::thread thread_;
  // Caller-thread state.
  bool closed_ = false, synchronous_ = false, contents_reset_ = false;
  SurfaceContents predicted_;
  std::map<SurfaceKey, std::weak_ptr<const Surface>> owners_;
  uint64_t commits_ = 0, timed_submits_ = 0;
  double wait_total_ms_ = 0, wait_max_ms_ = 0;
};
}  // namespace

std::unique_ptr<FrameBackend> MakeAsyncFrameBackend(std::unique_ptr<FrameBackend> backend,
                                                    void (*diagnostic)(const char*)) {
  if (!backend) return backend;
  return std::make_unique<AsyncFrameBackend>(std::move(backend), diagnostic);
}
}  // namespace theft4::render
