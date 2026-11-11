#pragma once

#include <cstdint>
#include <string_view>

// Identity of the single supported Episodes from Liberty City executable.
//
// The standalone EFLC disc shares title ID 545407F2 with Grand Theft Auto IV,
// so the title ID alone cannot distinguish the two games. The media ID and the
// exact executable/patch hashes are what select EFLC, and what keep the GTA IV
// app (which requires media 6AC07221) from accepting this disc.
namespace eflc::identity {

inline constexpr uint32_t kTitleId = 0x545407F2;

// TODO(eflc): fill in from the supported retail disc before enabling install
// validation. Zero means "not yet pinned" and validation must refuse to run.
inline constexpr uint32_t kSupportedMediaId = 0x00000000;
inline constexpr std::string_view kSupportedBaseXexSha256 = "";
inline constexpr std::string_view kSupportedPatchSha256 = "";
inline constexpr uint32_t kSupportedTargetVersion = 0x00000000;

inline constexpr bool IsPinned() {
  return kSupportedMediaId != 0 && !kSupportedBaseXexSha256.empty();
}

// Separate user-data root, so EFLC saves never mix with GTA IV saves. Both
// games would otherwise write to saves/<XUID>/545407F2/.
inline constexpr std::string_view kUserRootName = "EFLCRecomp";
inline constexpr std::string_view kAppName = "EFLC Recompiled";

}  // namespace eflc::identity
