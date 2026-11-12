#pragma once
// Runs a FrameBackend on its own encoder thread. Submit predicts the frame's
// published contents (PredictFrameContents), queues the frame and returns, so
// the renderer thread lowers the next frame while this one is encoded. Every
// other call runs on the encoder thread after queued work, so the wrapped
// backend still sees a single thread. One frame is in flight at a time.
//
// A wrapped failure, or a prediction that differs from the contents the
// backend actually published, is reported by the next call and switches the
// wrapper to synchronous submission for the rest of the session.
#include "theft4_frame_backend.h"
#include <memory>
namespace theft4::render {
std::unique_ptr<FrameBackend> MakeAsyncFrameBackend(std::unique_ptr<FrameBackend> backend,
                                                    void (*diagnostic)(const char*));
}
