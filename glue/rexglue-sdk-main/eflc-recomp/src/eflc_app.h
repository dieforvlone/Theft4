#pragma once

#include <filesystem>
#include <memory>
#include <string>

#include <rex/filesystem.h>
#include <rex/rex_app.h>

#include "eflc_identity.h"
#include "eflc_init.h"

// Minimal first-boot application: no title hooks, no installer, no native
// renderer extras. Its only job is to get the recompiled EFLC executable to
// its main menu so hooks can then be ported one at a time (see README.md).
class EFLCApp final : public rex::ReXApp {
 public:
  static std::unique_ptr<rex::ui::WindowedApp> Create(rex::ui::WindowedAppContext& context) {
    return std::unique_ptr<EFLCApp>(new EFLCApp(context));
  }

 private:
  explicit EFLCApp(rex::ui::WindowedAppContext& context)
      : ReXApp(context, eflc::identity::kAppName, PPCImageConfig) {}

  void OnConfigurePaths(rex::PathConfig& paths) override {
    const auto root =
        rex::filesystem::GetUserFolder() / std::string(eflc::identity::kUserRootName);
    const auto default_user_root = rex::filesystem::GetUserFolder() / std::string(GetName());

    // Until the EFLC installer exists, place an extracted disc (with the
    // title update's default.xexp beside default.xex) in <root>/game.
    if (paths.game_data_root.empty()) paths.game_data_root = root / "game";
    if (paths.user_data_root == default_user_root) paths.user_data_root = root / "saves";
    if (paths.saved_game_root.empty()) paths.saved_game_root = root / "saves";
    if (paths.cache_root == default_user_root / "cache") paths.cache_root = root / "shader_cache";
    paths.config_path = root / "native.toml";
    paths.marketplace_content_root = root / "dlc";

    std::error_code error;
    const auto update_root = paths.game_data_root / "update";
    if (paths.update_data_root.empty() && std::filesystem::is_directory(update_root, error)) {
      paths.update_data_root = update_root;
    }
  }
};
