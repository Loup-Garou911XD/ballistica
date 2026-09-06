// Released under the MIT License. See LICENSE for details.

#include "ballistica/remote/python/methods/python_methods_remote.h"

#include <vector>

#include "ballistica/base/base.h"
#include "ballistica/core/core.h"
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

// ----------------------- remote_app_mode_deactivate --------------------------

static auto PyRemoteAppModeDeactivate(PyObject* self) -> PyObject* {
  BA_PYTHON_TRY;
  BA_PRECONDITION(g_base->InLogicThread());
  // Our C++ app-mode's OnDeactivate() does the actual work.
  Py_RETURN_NONE;
  BA_PYTHON_CATCH;
}

static PyMethodDef PyRemoteAppModeDeactivateDef = {
    "remote_app_mode_deactivate",            // name
    (PyCFunction)PyRemoteAppModeDeactivate,  // method
    METH_NOARGS,                             // flags

    "remote_app_mode_deactivate() -> None\n"
    "\n"
    ":meta private:",
};

// ---------------- remote_app_mode_handle_app_intent_default ------------------

static auto PyRemoteAppModeHandleAppIntentDefault(PyObject* self) -> PyObject* {
  BA_PYTHON_TRY;
  BA_PRECONDITION(g_base->InLogicThread());
  // Nothing to do; our Python app-mode brings its own UI up on activate.
  Py_RETURN_NONE;
  BA_PYTHON_CATCH;
}

static PyMethodDef PyRemoteAppModeHandleAppIntentDefaultDef = {
    "remote_app_mode_handle_app_intent_default",         // name
    (PyCFunction)PyRemoteAppModeHandleAppIntentDefault,  // method
    METH_NOARGS,                                         // flags

    "remote_app_mode_handle_app_intent_default() -> None\n"
    "\n"
    ":meta private:\n",
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
  bool success = PythonCommand(command, BA_BUILD_COMMAND_FILENAME)
                     .Exec(true, nullptr, nullptr);
  if (!success) {
    // Matching EmptyAppMode here; intents have no success channel yet.
  }
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

// -----------------------------------------------------------------------------

auto PythonMethodsRemote::GetMethods() -> std::vector<PyMethodDef> {
  return {
      PyRemoteAppModeActivateDef,
      PyRemoteAppModeDeactivateDef,
      PyRemoteAppModeHandleAppIntentDefaultDef,
      PyRemoteAppModeHandleAppIntentExecDef,
      PySetInputAttachedDef,
  };
}

}  // namespace ballistica::remote
