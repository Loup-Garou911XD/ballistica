// Released under the MIT License. See LICENSE for details.

#ifndef BALLISTICA_REMOTE_PYTHON_REMOTE_PYTHON_H_
#define BALLISTICA_REMOTE_PYTHON_REMOTE_PYTHON_H_

#include "ballistica/remote/remote.h"
#include "ballistica/shared/python/python_object_set.h"

namespace ballistica::remote {

/// General Python support class for our feature-set.
class RemotePython {
 public:
  /// Hand a single input event up to Python. Logic thread only (which is
  /// where all input dispatch happens, so we already hold the GIL).
  void HandleInputCommand(InputType type, float value);

  /// Ask Python to put a ui back on screen.
  void RequestMainUI();

  /// Specific Python objects we hold in objs_.
  enum class ObjID {
    kHandleInputCommandCall,
    kRequestMainUICall,
    kLast  // Sentinel; must be at end.
  };

  void AddPythonClasses(PyObject* module);
  void ImportPythonObjs();
  const auto& objs() { return objs_; }

 private:
  PythonObjectSet<ObjID> objs_;
};

}  // namespace ballistica::remote

#endif  // BALLISTICA_REMOTE_PYTHON_REMOTE_PYTHON_H_
