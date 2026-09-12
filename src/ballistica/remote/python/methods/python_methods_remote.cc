// Released under the MIT License. See LICENSE for details.

#include "ballistica/remote/python/methods/python_methods_remote.h"

#include <cstdio>
#include <vector>

#include "ballistica/base/base.h"
#include "ballistica/core/core.h"
#include "ballistica/core/platform/platform.h"
#include "ballistica/remote/support/remote_app_mode.h"
#include "ballistica/remote/support/remote_input_delegate.h"
#include "ballistica/shared/python/python_command.h"
#include "ballistica/shared/python/python_macros.h"

namespace ballistica::remote {

// ------------------------ remote_app_mode_activate ---------------------------

static auto PyRemoteAppModeActivate(PyObject* self) -> PyObject* {
  BA_PYTHON_TRY;
  BA_PRECONDITION(g_base->InLogicThread());
  g_base->set_app_mode(RemoteAppMode::GetSingleton());
  Py_RETURN_NONE;
  BA_PYTHON_CATCH;
}

static PyMethodDef PyRemoteAppModeActivateDef = {
    "remote_app_mode_activate",            // name
    (PyCFunction)PyRemoteAppModeActivate,  // method
    METH_NOARGS,                           // flags

    "remote_app_mode_activate() -> None\n"
    "\n"
    ":meta private:",
};

// ------------------ remote_app_mode_handle_app_intent_exec -------------------

static auto PyRemoteAppModeHandleAppIntentExec(PyObject* self, PyObject* args,
                                               PyObject* keywds) -> PyObject* {
  BA_PYTHON_TRY;
  const char* command;
  static const char* kwlist[] = {"command", nullptr};
  if (!PyArg_ParseTupleAndKeywords(args, keywds, "s",
                                   const_cast<char**>(kwlist), &command)) {
    return nullptr;
  }
  // Return value ignored, matching EmptyAppMode; intents have no success
  // channel yet.
  PythonCommand(command, BA_BUILD_COMMAND_FILENAME)
      .Exec(true, nullptr, nullptr);
  Py_RETURN_NONE;
  BA_PYTHON_CATCH;
}

static PyMethodDef PyRemoteAppModeHandleAppIntentExecDef = {
    "remote_app_mode_handle_app_intent_exec",         // name
    (PyCFunction)PyRemoteAppModeHandleAppIntentExec,  // method
    METH_VARARGS | METH_KEYWORDS,                     // flags

    "remote_app_mode_handle_app_intent_exec(command: str) -> None\n"
    "\n"
    ":meta private:",
};

// ---------------------------- set_input_attached -----------------------------

static auto PySetInputAttached(PyObject* self, PyObject* args, PyObject* keywds)
    -> PyObject* {
  BA_PYTHON_TRY;
  BA_PRECONDITION(g_base->InLogicThread());
  int attached;
  static const char* kwlist[] = {"attached", nullptr};
  if (!PyArg_ParseTupleAndKeywords(args, keywds, "p",
                                   const_cast<char**>(kwlist), &attached)) {
    return nullptr;
  }
  RemoteInputDelegate::set_attached(static_cast<bool>(attached));
  Py_RETURN_NONE;
  BA_PYTHON_CATCH;
}

static PyMethodDef PySetInputAttachedDef = {
    "set_input_attached",             // name
    (PyCFunction)PySetInputAttached,  // method
    METH_VARARGS | METH_KEYWORDS,     // flags

    "set_input_attached(attached: bool) -> None\n"
    "\n"
    ":meta private:\n"
    "\n"
    "Tell the native layer whether we currently have a host to send input\n"
    "to. This gates input forwarding and is also what makes the engine's\n"
    "on-screen touch controls appear.",
};

// ---------------------------- get_broadcast_addrs ----------------------------

static auto PyGetBroadcastAddrs(PyObject* self) -> PyObject* {
  BA_PYTHON_TRY;
  auto addrs = g_core->platform->GetBroadcastAddrs();
  PyObject* list = PyList_New(0);
  for (uint32_t addr : addrs) {
    char buffer[16];
    snprintf(buffer, sizeof(buffer), "%d.%d.%d.%d",
             static_cast<int>((addr >> 24) & 0xFF),
             static_cast<int>((addr >> 16) & 0xFF),
             static_cast<int>((addr >> 8) & 0xFF),
             static_cast<int>(addr & 0xFF));
    PyObject* str = PyUnicode_FromString(buffer);
    PyList_Append(list, str);
    Py_DECREF(str);
  }
  return list;
  BA_PYTHON_CATCH;
}

static PyMethodDef PyGetBroadcastAddrsDef = {
    "get_broadcast_addrs",             // name
    (PyCFunction)PyGetBroadcastAddrs,  // method
    METH_NOARGS,                       // flags

    "get_broadcast_addrs() -> list[str]\n"
    "\n"
    ":meta private:\n"
    "\n"
    "The broadcast address of each of this machine's IPv4 interfaces,\n"
    "derived from their real netmasks. This is the same enumeration the\n"
    "engine's own LAN game scan uses.",
};

// -----------------------------------------------------------------------------

auto PythonMethodsRemote::GetMethods() -> std::vector<PyMethodDef> {
  return {
      PyRemoteAppModeActivateDef,
      PyRemoteAppModeHandleAppIntentExecDef,
      PySetInputAttachedDef,
      PyGetBroadcastAddrsDef,
  };
}

}  // namespace ballistica::remote
