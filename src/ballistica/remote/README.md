# Remote Feature Set

Turns the engine into a game controller for a BombSquad host on the local
network, speaking the same UDP protocol as the standalone BombSquad Remote
apps. The host side of that protocol lives in `base`
(`base/input/support/remote_app_server.cc`) and is the authoritative
definition of every layout involved.

Almost all of the work -- discovery, the protocol, the UI -- happens in
Python, in the `baremote` package. The C++ here exists for two things
Python cannot reach:

- `RemoteAppMode::OnActivate` registers `ui_v1` as the engine's
  ui-delegate. `ClassicAppMode` is the only other place that happens, so
  without this a classic-less build draws no widgets at all.
- `RemoteInputDelegate` intercepts `InputDeviceDelegate::InputCommand`,
  which is the single point every input device (keyboard, SDL gamepads,
  and the engine's own on-screen touch controls) funnels through.

Build a standalone remote app with `make spinoff-test-remote`, which spins
this repo off with only `core`, `base`, `ui_v1` and `remote`.
