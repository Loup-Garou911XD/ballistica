// Released under the MIT License. See LICENSE for details.

#include "ballistica/remote/support/remote_input_delegate.h"

#include <string>

#include "ballistica/base/base.h"
#include "ballistica/core/core.h"
#include "ballistica/remote/python/remote_python.h"

namespace ballistica::remote {

bool RemoteInputDelegate::attached_{};

RemoteInputDelegate::RemoteInputDelegate() = default;
RemoteInputDelegate::~RemoteInputDelegate() = default;

auto RemoteInputDelegate::DescribeAttachedTo() const -> std::string {
  return attached_ ? "remote-host" : "nothing";
}

void RemoteInputDelegate::InputCommand(InputType type, float value) {
  assert(g_base->InLogicThread());

  // Don't bother waking Python up when we've nowhere to send input.
  if (!attached_) {
    return;
  }
  g_remote->python->HandleInputCommand(type, value);
}

}  // namespace ballistica::remote
