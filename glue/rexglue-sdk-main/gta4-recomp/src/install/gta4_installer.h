#pragma once

#include <atomic>
#include <filesystem>
#include <string>
#include <vector>

#include "gta4_source_inspector.h"

namespace gta4::install {

enum class Episode {
  kTlad,
  kTbogt,
};

struct DlcSelection {
  Episode episode;
  std::filesystem::path source;
};

struct Selection {
  std::filesystem::path game_source;
  std::filesystem::path update_source;
  std::vector<DlcSelection> dlc_sources;
};

struct Progress {
  std::atomic<uint64_t> copied_bytes{0};
  std::atomic<uint64_t> total_bytes{0};
  std::atomic<bool> cancel_requested{false};
};

struct Result {
  bool success = false;
  std::string error;
};

bool IsInstallReady(const std::filesystem::path& game_root, std::string* reason = nullptr);
// Installs and validates a supported title update for an already-copied retail
// game directory. The update source may be either an STFS package or a raw
// default.xexp patch; the base game is never copied or replaced.
Result InstallTitleUpdate(const std::filesystem::path& game_root,
                          const std::filesystem::path& update_source);
bool IsEpisodeReady(const std::filesystem::path& marketplace_root, Episode episode);

struct EpisodeInstallResult {
  bool success = false;
  std::string error;
  bool installed_tlad = false;
  bool installed_tbogt = false;
};
// Searches one source (a disc image, an Xbox content package or an extracted
// folder) for The Lost and Damned and The Ballad of Gay Tony, and installs
// every episode found into marketplace_root/TLAD and marketplace_root/TBOGT.
// Requires a launch-ready base game at game_root. Episodes already installed
// are replaced only after the new copy has been staged and validated.
EpisodeInstallResult InstallEpisodesFromSource(const std::filesystem::path& game_root,
                                               const std::filesystem::path& marketplace_root,
                                               const std::filesystem::path& source,
                                               Progress& progress);
Result VerifyInstall(const std::filesystem::path& game_root,
                     const std::filesystem::path& marketplace_root);
Result Install(const Selection& selection, const std::filesystem::path& install_root,
               Progress& progress);

const char* EpisodeDirectory(Episode episode);

}  // namespace gta4::install
