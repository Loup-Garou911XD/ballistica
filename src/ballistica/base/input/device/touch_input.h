// Released under the MIT License. See LICENSE for details.

#ifndef BALLISTICA_BASE_INPUT_DEVICE_TOUCH_INPUT_H_
#define BALLISTICA_BASE_INPUT_DEVICE_TOUCH_INPUT_H_

#include <optional>
#include <string>

#include "ballistica/base/input/device/input_device.h"
#include "ballistica/shared/math/vector3f.h"

namespace ballistica::base {

/// A touchscreen based controller for mobile devices.
class TouchInput : public InputDevice {
 public:
  TouchInput();
  ~TouchInput() override;
  auto GetAllowsConfiguring() -> bool override { return false; }
  void HandleTouchEvent(TouchEvent::Type type, void* touch, float x, float y);
  auto HandleTouchDown(void* touch, float x, float y) -> bool;
  auto HandleTouchUp(void* touch, float x, float y) -> bool;
  auto HandleTouchMoved(void* touch, float x, float y) -> bool;
  void Draw(FrameDef* frame_def);
  void set_editing(bool e) { editing_ = e; }
  auto editing() const -> bool { return editing_; }
  auto IsTouchScreen() -> bool override { return true; }
  void ApplyAppConfig() override;
  enum class MovementControlType { kJoystick, kSwipe };
  enum class ActionControlType { kButtons, kSwipe };

  /// Whether the supplied action-button meshes carry their own position
  /// offsets within the button cluster. Classic's do, and that is why no
  /// spread is applied when drawing them. An app-mode supplying plain
  /// quads instead (see babase.BaseAssetSet) turns this off so the
  /// cluster gets laid out at draw time; leaving it on would stack all
  /// four buttons on the same spot.
  void set_action_button_meshes_prepositioned(bool val) {
    action_button_meshes_prepositioned_ = val;
  }

  /// Pin the movement style, ignoring the app-config setting. For
  /// app-modes that bring these controls up themselves and have a
  /// specific style in mind (see AppMode::ForcesOnScreenControls); pass
  /// nullopt to go back to honoring the config.
  void set_movement_control_type_override(
      std::optional<MovementControlType> val) {
    movement_control_type_override_ = val;
    if (val.has_value()) {
      movement_control_type_ = *val;
    }
  }

 protected:
  auto DoGetDeviceName() -> std::string override;

 private:
  void UpdateDPad();
  void UpdateButtons(bool new_touch = false);
  MovementControlType movement_control_type_{MovementControlType::kSwipe};
  std::optional<MovementControlType> movement_control_type_override_;
  bool action_button_meshes_prepositioned_{true};
  ActionControlType action_control_type_{ActionControlType::kButtons};
  float controls_scale_move_{1.0f};
  float controls_scale_actions_{1.0f};
  bool swipe_controls_hidden_{};
  float presence_{};
  float button_fade_{};
  bool editing_{};
  void* d_pad_touch_{};
  void* d_pad_drag_touch_{};
  float d_pad_drag_x_offs_{};
  float d_pad_drag_y_offs_{};
  float d_pad_start_x_{};
  float d_pad_start_y_{};
  bool did_first_move_{};
  float d_pad_base_x_{};
  float d_pad_base_y_{};
  float d_pad_x_{};
  float d_pad_y_{};

  // Button coordinates are provided in virtual screen space.
  float buttons_default_frac_x_{};
  float buttons_default_frac_y_{};
  float d_pad_default_frac_x_{};
  float d_pad_default_frac_y_{};
  float buttons_x_{-100.0f};
  float buttons_y_{-100.0f};
  float buttons_touch_start_x_{};
  float buttons_touch_start_y_{};
  void* buttons_touch_{};
  float buttons_touch_x_{-100.0f};
  float buttons_touch_y_{-100.0f};
  void* buttons_drag_touch_{};
  float buttons_drag_x_offs_{};
  float buttons_drag_y_offs_{};
  float base_controls_scale_{1.0f};
  float world_draw_scale_{1.0f};
  bool bomb_held_{};
  bool punch_held_{};
  bool jump_held_{};
  bool pickup_held_{};
  float d_pad_draw_x_{};
  float d_pad_draw_y_{};
  Vector3f d_pad_draw_dir_{1.0f, 0.0f, 0.0f};
  millisecs_t last_buttons_touch_time_{};
  millisecs_t last_punch_held_time_{};
  millisecs_t last_pickup_held_time_{};
  millisecs_t last_bomb_held_time_{};
  millisecs_t last_jump_held_time_{};
  millisecs_t last_punch_press_time_{};
  millisecs_t last_pickup_press_time_{};
  millisecs_t last_bomb_press_time_{};
  millisecs_t last_jump_press_time_{};
  millisecs_t update_time_{};
};

}  // namespace ballistica::base

#endif  // BALLISTICA_BASE_INPUT_DEVICE_TOUCH_INPUT_H_
