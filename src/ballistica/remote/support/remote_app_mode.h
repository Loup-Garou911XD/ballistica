// Released under the MIT License. See LICENSE for details.

#ifndef BALLISTICA_REMOTE_SUPPORT_REMOTE_APP_MODE_H_
#define BALLISTICA_REMOTE_SUPPORT_REMOTE_APP_MODE_H_

#include "ballistica/base/app_mode/app_mode.h"
#include "ballistica/remote/remote.h"

namespace ballistica::remote {

/// App-mode for the remote-control app.
///
/// It has two jobs, both of which have to happen in C++:
///
/// - Registering ui_v1 as the engine's ui-delegate. ClassicAppMode is the
///   only other place in the engine that does this, so without us a
///   classic-less build draws no widgets at all.
/// - Handing out RemoteInputDelegates so local input can be forwarded to
///   Python and shipped to the host.
///
/// Everything else (discovery, the protocol, the UI) lives in Python.
class RemoteAppMode : public base::AppMode {
 public:
  static auto GetSingleton() -> RemoteAppMode*;

  void OnActivate() override;
  void OnDeactivate() override;

  auto CreateInputDeviceDelegate(base::InputDevice* device)
      -> base::InputDeviceDelegate* override;

  /// Fired when an input device asks for a ui while none is up. With the
  /// controls hidden (which is what lets input reach us at all) this is
  /// the player's only way back to a menu, so route it to Python.
  void RequestMainUI() override;

  /// We are a controller, not a host: never advertise ourselves as a game
  /// to connect to, and never answer our own discovery broadcasts.
  auto AcceptsRemoteAppConnections() const -> bool override;

  /// Nor do we ever listen. Our client socket sends from an ephemeral
  /// port and hosts reply to it there, so binding the game port would do
  /// nothing but keep a real game on this machine from hosting.
  auto WantsUDPListener() const -> bool override;

  /// Being a controller is the whole app, so we want the engine's own
  /// on-screen stick and action buttons wherever we run -- not just on
  /// the phones that normally get them.
  auto ForcesOnScreenControls() const -> bool override;

 private:
  RemoteAppMode();

  ui_v1::UIV1FeatureSet* uiv1_{};
};

}  // namespace ballistica::remote

#endif  // BALLISTICA_REMOTE_SUPPORT_REMOTE_APP_MODE_H_
