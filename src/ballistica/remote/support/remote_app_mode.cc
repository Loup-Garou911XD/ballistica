// Released under the MIT License. See LICENSE for details.

#include "ballistica/remote/support/remote_app_mode.h"

#include "ballistica/base/base.h"
#include "ballistica/base/graphics/graphics.h"
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

auto RemoteAppMode::CreateInputDeviceDelegate(base::InputDevice* device)
    -> base::InputDeviceDelegate* {
  return Object::NewDeferred<RemoteInputDelegate>();
}

void RemoteAppMode::RequestMainUI() {
  assert(g_base->InLogicThread());
  g_remote->python->RequestMainUI();
}

}  // namespace ballistica::remote
