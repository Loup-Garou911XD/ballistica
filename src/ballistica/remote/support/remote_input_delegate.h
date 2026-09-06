// Released under the MIT License. See LICENSE for details.

#ifndef BALLISTICA_REMOTE_SUPPORT_REMOTE_INPUT_DELEGATE_H_
#define BALLISTICA_REMOTE_SUPPORT_REMOTE_INPUT_DELEGATE_H_

#include <string>

#include "ballistica/base/input/device/input_device_delegate.h"
#include "ballistica/remote/remote.h"

namespace ballistica::remote {

/// Input-device-delegate that forwards everything to Python.
///
/// Every input device the engine knows about (keyboard, SDL gamepads and
/// the engine's own on-screen touch controls) funnels its input through
/// InputDeviceDelegate::InputCommand(), so intercepting it here is what
/// lets us turn local input into remote-app state packets.
///
/// Note that input only reaches us when no main-ui is visible; with a
/// bauiv1 window on screen the engine routes input to widget navigation
/// instead (see JoystickInput::HandleSDLEvent). That is what makes our
/// two control surfaces mutually exclusive.
class RemoteInputDelegate : public base::InputDeviceDelegate {
 public:
  RemoteInputDelegate();
  ~RemoteInputDelegate() override;

  /// Whether we're currently acting as a controller. This is global
  /// rather than per-delegate; it reflects whether the app as a whole is
  /// connected to a host.
  static auto attached() -> bool { return attached_; }
  static void set_attached(bool val) { attached_ = val; }

  void InputCommand(InputType type, float value) override;

  /// Returning true here is what makes the engine's on-screen touch
  /// controls draw themselves and start feeding us (see TouchInput::Draw).
  auto AttachedToPlayer() const -> bool override { return attached_; }

  auto DescribeAttachedTo() const -> std::string override;

  /// A press on an unattached device lands here. We have nothing to join,
  /// so this is a no-op; connecting happens through our own UI.
  void RequestPlayer() override {}

 private:
  static bool attached_;
};

}  // namespace ballistica::remote

#endif  // BALLISTICA_REMOTE_SUPPORT_REMOTE_INPUT_DELEGATE_H_
