#pragma once
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
// One-shot loader preparation. Call on a background queue; callbacks run on
// that queue. No UI or core-handle access is permitted from the callback.
typedef void (*theft4_boot_event_fn)(void* context, const char* event);
// Call on the host main thread before starting the loader worker.
int theft4_configure_boot_diagnostics(void);
// Imports a raw STFS title-update package or default.xexp selected through the
// iOS Files picker. The update is validated against the existing base game and
// installed below game_directory. Call on a background queue.
// Returns zero on success and writes a short user-facing result to message.
int theft4_install_title_update(const char* game_directory, const char* update_source,
                                char* message, size_t message_capacity);

// Episodes from Liberty City. The source may be an EFLC disc image (.iso),
// an Xbox content package, or an extracted folder; it is searched for The Lost
// and Damned and The Ballad of Gay Tony and every episode found is installed
// into the game's marketplace folder below support_directory. Requires a
// launch-ready base game. progress (optional) is called on a helper thread
// with copied/total bytes. Call on a background queue. Returns zero on success;
// installed_mask receives THEFT4_EPISODE_* bits for the episodes installed.
#define THEFT4_EPISODE_TLAD 1u
#define THEFT4_EPISODE_TBOGT 2u
typedef void (*theft4_progress_fn)(void* context, unsigned long long copied,
                                   unsigned long long total);
int theft4_install_episodes(const char* game_directory, const char* support_directory,
                            const char* episode_source, theft4_progress_fn progress,
                            void* context, unsigned* installed_mask,
                            char* message, size_t message_capacity);
// THEFT4_EPISODE_* bits for the episodes that are installed and complete.
unsigned theft4_installed_episodes(const char* support_directory);

// Validates a transferred extracted base game before the app lets the user
// select a title update. This only reads the selected directory.
int theft4_validate_base_game(const char* game_directory, char* message,
                              size_t message_capacity);
// Validates an already-installed base/TU8 pair without writing to it.
int theft4_validate_installed_game(const char* game_directory, char* message,
                                   size_t message_capacity);
int theft4_prepare_game(const char* game_directory, const char* support_directory,
                       theft4_boot_event_fn event, void* context);
// Experimental one-shot execution. Call off the main thread after diagnostics
// setup, with no other runtime active. Missing media/UI exports stop the app.
int theft4_start_game(const char* game_directory, const char* support_directory,
                     theft4_boot_event_fn event, void* context);
// Heat Guard. Call on the main thread whenever the thermal state changes
// (0 nominal, 1 fair, 2 serious, 3 critical) while the game runs. At serious
// and above it shortens the draw and shadow distances chosen at launch; below
// serious it restores them. No effect before the game starts.
void theft4_heat_guard_apply(int thermal_state);
#ifdef __cplusplus
}
#endif
