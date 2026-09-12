// Released under the MIT License. See LICENSE for details.

#include "ballistica/remote/support/remote_app_mode.h"

#include "ballistica/base/base.h"
#include "ballistica/base/graphics/graphics.h"
#include "ballistica/base/input/device/input_device.h"
#include "ballistica/base/input/device/touch_input.h"
#include "ballistica/base/input/input.h"
#include "ballistica/base/ui/ui.h"
#include "ballistica/core/core.h"
#include "ballistica/remote/python/remote_python.h"
#include "ballistica/remote/support/remote_input_delegate.h"
#include "ballistica/ui_v1/ui_v1.h"

namespace ballistica::remote {

static RemoteAppMode* g_remote_app_mode{};

RemoteAppMode::RemoteAppMode() = default;

auto RemoteAppMode::GetSingleton() -> RemoteAppMode* {
  assert(g_base == nullptr || g_base->InLogicThread());

  if (g_remote_app_mode == nullptr) {
    g_remote_app_mode = new RemoteAppMode();
  }
  return g_remote_app_mode;
}

void RemoteAppMode::OnActivate() {
  assert(g_base->InLogicThread());

  // Reset the engine itself to a default state.
  g_base->Reset();

  // Import UIV1 and wire it up for UI duty. ClassicAppMode is the only
  // other place this happens, so in a classic-less build we are the only
  // thing standing between ui_v1 and a blank screen.
  if (!g_core->HeadlessMode()) {
    uiv1_ = ui_v1::UIV1FeatureSet::Import();
    g_base->ui->SetUIDelegate(uiv1_);

    // Nothing has faded us in yet at this point; do it ourselves or we
    // sit at a black screen forever.
    g_base->graphics->FadeScreen(true, 250, nullptr);

    // Our action-button art is plain quads from the builtin package
    // rather than classic's pre-positioned meshes (see
    // baremote._baseassets), so the cluster has to be laid out at draw
    // time or all four buttons land on the same spot.
    if (auto* touch = g_base->input->touch_input()) {
      touch->set_action_button_meshes_prepositioned(false);
    }
  }
}

void RemoteAppMode::OnDeactivate() {
  assert(g_base->InLogicThread());

  // Any input arriving between here and our next activation has nowhere
  // to go.
  RemoteInputDelegate::set_attached(false);

  if (uiv1_ != nullptr) {
    g_base->ui->SetUIDelegate(nullptr);
    uiv1_ = nullptr;
  }
}

auto RemoteAppMode::AcceptsRemoteAppConnections() const -> bool {
  return false;
}

auto RemoteAppMode::WantsUDPListener() const -> bool { return false; }

auto RemoteAppMode::ForcesOnScreenControls() const -> bool { return true; }

auto RemoteAppMode::CreateInputDeviceDelegate(base::InputDevice* device)
    -> base::InputDeviceDelegate* {
  return Object::NewDeferred<RemoteInputDelegate>();
}

void RemoteAppMode::RequestMainUI() {
  assert(g_base->InLogicThread());

  // Escape and a gamepad's start button both land here, and they mean
  // opposite things for us: start is the host's pause button, while
  // escape is a 'back' aimed at our own ui. UI::RequestMainUI_ records
  // the device that asked just before calling us, so that is how we tell
  // them apart.
  //
  // Only a real controller counts as start. The engine resolves the
  // escape key's device 'fuzzily' (Input::GetFuzzyInputDeviceForEscapeKey)
  // and can hand back whichever device happens to be attached to a
  // player -- and every device looks attached to us while we are
  // connected, since RemoteInputDelegate tracks that globally. Asking
  // for a controller specifically keeps an ambiguous attribution on the
  // safe side: our own ui, rather than a stray press sent to the host.
  auto* device = g_base->ui->GetMainUIInputDevice();
  bool from_controller = device != nullptr && device->IsController();

  g_remote->python->RequestMainUI(from_controller);
}

}  // namespace ballistica::remote
