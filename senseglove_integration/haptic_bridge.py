"""
Haptic Bridge - Robot Hand to SenseGlove integration GUI.

Maps RH56DFTP tactile and force feedback data to a right-hand SenseGlove.

Usage:
    python haptic_bridge.py [--network INTERFACE] [--simulate] [--no-robot]
"""

import os
import sys
import time
import threading

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'inspire_hand_sdk'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'unitree_sdk2_python'))

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSlider,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from senseglove_client import EHapticLocation, SenseGloveClient, SenseGloveSimulator


ROBOT_FINGER_NAMES = ["小拇指", "无名指", "中指", "食指", "拇指弯曲", "拇指旋转"]
SG_FINGER_NAMES = ["拇指", "食指", "中指", "无名指", "小拇指"]

FORCE_MAP = {
    0: 4,
    1: 3,
    2: 2,
    3: 1,
    4: 0,
}

TOUCH_VIBRO_MAP = {
    "pinky": EHapticLocation.PinkyTip,
    "ring": EHapticLocation.RingTip,
    "middle": EHapticLocation.MiddleTip,
    "index": EHapticLocation.IndexTip,
    "thumb": EHapticLocation.ThumbTip,
    "palm": EHapticLocation.WholeHand,
}


class RobotHandDDS:
    def __init__(self, network=None, lr='r'):
        from unitree_sdk2py.core.channel import (
            ChannelFactoryInitialize,
            ChannelPublisher,
            ChannelSubscriber,
        )
        from inspire_sdkpy import inspire_dds, inspire_hand_defaut

        if network is None:
            ChannelFactoryInitialize(0)
        else:
            ChannelFactoryInitialize(0, network)

        self._inspire_dds = inspire_dds
        self._inspire_hand_defaut = inspire_hand_defaut
        self.data_sheet = inspire_hand_defaut.data_sheet
        self.lr = lr
        self.states = {
            "POS_ACT": [0] * 6,
            "ANGLE_ACT": [0] * 6,
            "FORCE_ACT": [0] * 6,
            "CURRENT": [0] * 6,
            "ERROR": [0] * 6,
            "STATUS": [0] * 6,
            "TEMP": [0] * 6,
        }
        self.touch = {}
        self._state_lock = threading.Lock()
        self._touch_lock = threading.Lock()

        self.sub_state = ChannelSubscriber(
            f"rt/inspire_hand/state/{lr}", inspire_dds.inspire_hand_state
        )
        self.sub_state.Init(self._on_state, 10)

        self.sub_touch = ChannelSubscriber(
            f"rt/inspire_hand/touch/{lr}", inspire_dds.inspire_hand_touch
        )
        self.sub_touch.Init(self._on_touch, 10)

        self.pub_ctrl = ChannelPublisher(
            f"rt/inspire_hand/ctrl/{lr}", inspire_dds.inspire_hand_ctrl
        )
        self.pub_ctrl.Init()

    def _on_state(self, msg):
        with self._state_lock:
            self.states = {
                "POS_ACT": list(msg.pos_act),
                "ANGLE_ACT": list(msg.angle_act),
                "FORCE_ACT": list(msg.force_act),
                "CURRENT": list(msg.current),
                "ERROR": list(msg.err),
                "STATUS": list(msg.status),
                "TEMP": list(msg.temperature),
            }

    def _on_touch(self, msg):
        with self._touch_lock:
            for _, _, _, size, var in self.data_sheet:
                value = getattr(msg, var)
                if value is not None:
                    self.touch[var] = np.array(value).reshape(size)

    def get_states(self):
        with self._state_lock:
            return dict(self.states)

    def get_force_act(self):
        with self._state_lock:
            return list(self.states["FORCE_ACT"])

    def get_finger_touch_intensity(self):
        with self._touch_lock:
            result = {}
            mappings = [
                ("pinky", ["fingerone_tip_touch", "fingerone_top_touch", "fingerone_palm_touch"]),
                ("ring", ["fingertwo_tip_touch", "fingertwo_top_touch", "fingertwo_palm_touch"]),
                ("middle", ["fingerthree_tip_touch", "fingerthree_top_touch", "fingerthree_palm_touch"]),
                ("index", ["fingerfour_tip_touch", "fingerfour_top_touch", "fingerfour_palm_touch"]),
                ("thumb", ["fingerfive_tip_touch", "fingerfive_top_touch", "fingerfive_middle_touch", "fingerfive_palm_touch"]),
                ("palm", ["palm_touch"]),
            ]
            for name, vars_list in mappings:
                total = 0.0
                count = 0
                for var in vars_list:
                    if var in self.touch:
                        total += float(np.mean(self.touch[var].astype(float)))
                        count += 1
                intensity = (total / max(count, 1)) / 500.0 if count > 0 else 0.0
                result[name] = min(1.0, max(0.0, intensity))
            return result

    def send_ctrl(self, pos_set=None, angle_set=None, force_set=None, speed_set=None):
        msg = self._inspire_hand_defaut.get_inspire_hand_ctrl()
        if pos_set is not None:
            msg.pos_set = pos_set
        if angle_set is not None:
            msg.angle_set = angle_set
        if force_set is not None:
            msg.force_set = force_set
        if speed_set is not None:
            msg.speed_set = speed_set
        self.pub_ctrl.Write(msg)


class FakeRobotHand:
    def __init__(self):
        self._force = [0.0] * 6
        self._touch = {name: 0.0 for name in TOUCH_VIBRO_MAP}

    def get_states(self):
        return {
            "POS_ACT": [500] * 6,
            "ANGLE_ACT": [0] * 6,
            "FORCE_ACT": [int(value * 1000) for value in self._force],
            "CURRENT": [0] * 6,
            "ERROR": [0] * 6,
            "STATUS": [0] * 6,
            "TEMP": [25] * 6,
        }

    def get_force_act(self):
        return [int(value * 1000) for value in self._force]

    def get_finger_touch_intensity(self):
        return dict(self._touch)

    def set_simulated_force(self, index, value):
        self._force[index] = value

    def set_simulated_touch(self, name, value):
        self._touch[name] = value


class FingerBar(QWidget):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self.label = QLabel(name)
        self.label.setFixedWidth(60)
        self.label.setFont(QFont("Microsoft YaHei", 8))
        layout.addWidget(self.label)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFormat("%v%%")
        self.bar.setTextVisible(True)
        layout.addWidget(self.bar)

    def set_value(self, value):
        self.bar.setValue(int(max(0, min(100, value * 100))))


class HapticBridgeWindow(QMainWindow):
    def __init__(self, robot, sg_client, simulate_robot=False):
        super().__init__()
        self.robot = robot
        self.sg = sg_client
        self.simulate_robot = simulate_robot
        self.bridge_active = False
        self.tick_count = 0
        self.tick_window_start = time.time()

        self.setWindowTitle("触觉桥接 - RH56DFTP 与 SenseGlove")
        self.setMinimumSize(920, 720)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        status_group = QGroupBox("连接状态")
        status_layout = QGridLayout(status_group)
        self.robot_status_label = QLabel("机械手: 等待数据")
        self.sg_status_label = QLabel("SenseGlove: 初始化中")
        status_layout.addWidget(self.robot_status_label, 0, 0)
        status_layout.addWidget(self.sg_status_label, 0, 1)
        self.refresh_button = QPushButton("刷新 SenseGlove 状态")
        self.refresh_button.clicked.connect(self.refresh_senseglove)
        status_layout.addWidget(self.refresh_button, 0, 2)
        main_layout.addWidget(status_group)

        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        bridge_tab = QWidget()
        bridge_layout = QVBoxLayout(bridge_tab)

        control_row = QHBoxLayout()
        self.bridge_button = QPushButton("启动桥接")
        self.bridge_button.clicked.connect(self.toggle_bridge)
        control_row.addWidget(self.bridge_button)
        control_row.addWidget(QLabel("更新频率"))
        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(5.0, 100.0)
        self.rate_spin.setValue(20.0)
        self.rate_spin.setSuffix(" Hz")
        control_row.addWidget(self.rate_spin)
        control_row.addStretch()
        bridge_layout.addLayout(control_row)

        params_group = QGroupBox("映射参数")
        params_layout = QGridLayout(params_group)

        self.force_gain = QDoubleSpinBox()
        self.force_gain.setRange(0.1, 10.0)
        self.force_gain.setSingleStep(0.1)
        self.force_gain.setValue(1.0)
        params_layout.addWidget(QLabel("力反馈增益"), 0, 0)
        params_layout.addWidget(self.force_gain, 0, 1)

        self.force_threshold = QDoubleSpinBox()
        self.force_threshold.setRange(0.0, 1.0)
        self.force_threshold.setSingleStep(0.01)
        self.force_threshold.setValue(0.05)
        params_layout.addWidget(QLabel("力反馈阈值"), 0, 2)
        params_layout.addWidget(self.force_threshold, 0, 3)

        self.vibro_gain = QDoubleSpinBox()
        self.vibro_gain.setRange(0.1, 10.0)
        self.vibro_gain.setSingleStep(0.1)
        self.vibro_gain.setValue(2.0)
        params_layout.addWidget(QLabel("振动增益"), 1, 0)
        params_layout.addWidget(self.vibro_gain, 1, 1)

        self.vibro_duration = QDoubleSpinBox()
        self.vibro_duration.setRange(0.01, 1.0)
        self.vibro_duration.setSingleStep(0.01)
        self.vibro_duration.setValue(0.05)
        params_layout.addWidget(QLabel("振动时长"), 1, 2)
        params_layout.addWidget(self.vibro_duration, 1, 3)

        self.vibro_frequency = QDoubleSpinBox()
        self.vibro_frequency.setRange(10.0, 300.0)
        self.vibro_frequency.setSingleStep(10.0)
        self.vibro_frequency.setValue(80.0)
        params_layout.addWidget(QLabel("振动频率"), 2, 0)
        params_layout.addWidget(self.vibro_frequency, 2, 1)

        self.enable_ffb = QCheckBox("启用力反馈")
        self.enable_ffb.setChecked(True)
        params_layout.addWidget(self.enable_ffb, 2, 2)

        self.enable_vibro = QCheckBox("启用振动")
        self.enable_vibro.setChecked(True)
        params_layout.addWidget(self.enable_vibro, 2, 3)

        bridge_layout.addWidget(params_group)

        monitor_row = QHBoxLayout()

        sg_ffb_group = QGroupBox("SenseGlove 力反馈输出")
        sg_ffb_layout = QVBoxLayout(sg_ffb_group)
        self.sg_ffb_bars = {}
        for name in SG_FINGER_NAMES:
            widget = FingerBar(name)
            self.sg_ffb_bars[name] = widget
            sg_ffb_layout.addWidget(widget)
        monitor_row.addWidget(sg_ffb_group)

        sg_vibro_group = QGroupBox("SenseGlove 振动输出")
        sg_vibro_layout = QVBoxLayout(sg_vibro_group)
        self.sg_vibro_bars = {}
        touch_labels = {
            "pinky": "小拇指",
            "ring": "无名指",
            "middle": "中指",
            "index": "食指",
            "thumb": "拇指",
            "palm": "手掌",
        }
        for key, name in touch_labels.items():
            widget = FingerBar(name)
            self.sg_vibro_bars[key] = widget
            sg_vibro_layout.addWidget(widget)
        monitor_row.addWidget(sg_vibro_group)

        robot_group = QGroupBox("机械手原始力数据")
        robot_layout = QVBoxLayout(robot_group)
        self.robot_bars = {}
        for name in ROBOT_FINGER_NAMES:
            widget = FingerBar(name)
            self.robot_bars[name] = widget
            robot_layout.addWidget(widget)
        monitor_row.addWidget(robot_group)

        bridge_layout.addLayout(monitor_row)
        tabs.addTab(bridge_tab, "桥接")

        if simulate_robot:
            simulate_tab = QWidget()
            simulate_layout = QVBoxLayout(simulate_tab)

            force_group = QGroupBox("模拟力输入")
            force_layout = QVBoxLayout(force_group)
            self.sim_force_sliders = []
            for index, name in enumerate(ROBOT_FINGER_NAMES[:5]):
                row = QHBoxLayout()
                row.addWidget(QLabel(name))
                slider = QSlider(Qt.Horizontal)
                slider.setRange(0, 100)
                slider.setValue(0)
                slider.valueChanged.connect(
                    lambda value, idx=index: self.robot.set_simulated_force(idx, value / 100.0)
                )
                row.addWidget(slider)
                force_layout.addLayout(row)
                self.sim_force_sliders.append(slider)
            simulate_layout.addWidget(force_group)

            touch_group = QGroupBox("模拟触觉输入")
            touch_layout = QVBoxLayout(touch_group)
            self.sim_touch_sliders = {}
            for key, label in touch_labels.items():
                row = QHBoxLayout()
                row.addWidget(QLabel(label))
                slider = QSlider(Qt.Horizontal)
                slider.setRange(0, 100)
                slider.setValue(0)
                slider.valueChanged.connect(
                    lambda value, name=key: self.robot.set_simulated_touch(name, value / 100.0)
                )
                row.addWidget(slider)
                touch_layout.addLayout(row)
                self.sim_touch_sliders[key] = slider
            simulate_layout.addWidget(touch_group)
            tabs.addTab(simulate_tab, "模拟")

        self.stop_button = QPushButton("紧急停止所有反馈")
        self.stop_button.clicked.connect(self.emergency_stop)
        main_layout.addWidget(self.stop_button)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("就绪")

        self.bridge_timer = QTimer()
        self.bridge_timer.timeout.connect(self.bridge_tick)

        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self.update_display)
        self.display_timer.start(100)

        QTimer.singleShot(300, self.refresh_senseglove)

    def refresh_senseglove(self):
        try:
            init_response = self.sg.init()
            status_response = self.sg.get_status()
            if init_response.get("ok"):
                suffix = status_response.get("type", "未识别") if status_response.get("right_connected") else "未连接"
                self.sg_status_label.setText(
                    f"SenseGlove: {'已连接' if status_response.get('right_connected') else '未连接'} | {suffix}"
                )
            else:
                self.sg_status_label.setText(f"SenseGlove: 初始化失败 - {init_response.get('error', '?')}")
        except Exception as exc:
            self.sg_status_label.setText(f"SenseGlove: 通信错误 - {exc}")

    def toggle_bridge(self):
        if self.bridge_active:
            self.stop_bridge()
        else:
            self.start_bridge()

    def start_bridge(self):
        interval_ms = int(1000.0 / self.rate_spin.value())
        self.bridge_active = True
        self.bridge_timer.start(interval_ms)
        self.bridge_button.setText("停止桥接")
        self.statusBar().showMessage("桥接已启动")

    def stop_bridge(self):
        self.bridge_active = False
        self.bridge_timer.stop()
        self.sg.stop_haptics()
        self.bridge_button.setText("启动桥接")
        self.statusBar().showMessage("桥接已停止")

    def emergency_stop(self):
        self.stop_bridge()
        try:
            self.sg.stop_haptics()
        except Exception:
            pass
        self.statusBar().showMessage("已执行紧急停止")

    def bridge_tick(self):
        try:
            force_raw = self.robot.get_force_act()
            threshold = self.force_threshold.value()

            if self.enable_ffb.isChecked():
                sg_levels = [0.0] * 5
                for robot_index, sg_index in FORCE_MAP.items():
                    level = min(1.0, max(0.0, (force_raw[robot_index] / 1000.0) * self.force_gain.value()))
                    if level < threshold:
                        level = 0.0
                    sg_levels[sg_index] = level
                self.sg.set_force_feedback(sg_levels)

            if self.enable_vibro.isChecked():
                touch = self.robot.get_finger_touch_intensity()
                for name, location in TOUCH_VIBRO_MAP.items():
                    level = min(1.0, max(0.0, touch.get(name, 0.0) * self.vibro_gain.value()))
                    if level >= threshold:
                        self.sg.send_waveform(
                            level,
                            self.vibro_duration.value(),
                            self.vibro_frequency.value(),
                            location,
                        )

            self.tick_count += 1
        except Exception as exc:
            self.statusBar().showMessage(f"桥接错误: {exc}")

    def update_display(self):
        try:
            states = self.robot.get_states()
            force_raw = states["FORCE_ACT"]
            for index, name in enumerate(ROBOT_FINGER_NAMES):
                self.robot_bars[name].set_value(force_raw[index] / 1000.0)
            self.robot_status_label.setText(f"机械手: 力数据 {force_raw[:5]}")

            if self.bridge_active and self.enable_ffb.isChecked():
                preview = [0.0] * 5
                for robot_index, sg_index in FORCE_MAP.items():
                    level = min(1.0, max(0.0, (force_raw[robot_index] / 1000.0) * self.force_gain.value()))
                    if level < self.force_threshold.value():
                        level = 0.0
                    preview[sg_index] = level
                for index, name in enumerate(SG_FINGER_NAMES):
                    self.sg_ffb_bars[name].set_value(preview[index])
            else:
                for widget in self.sg_ffb_bars.values():
                    widget.set_value(0.0)

            touch = self.robot.get_finger_touch_intensity()
            for key, widget in self.sg_vibro_bars.items():
                value = min(1.0, max(0.0, touch.get(key, 0.0) * self.vibro_gain.value()))
                widget.set_value(value if self.bridge_active and self.enable_vibro.isChecked() else touch.get(key, 0.0))

            now = time.time()
            dt = now - self.tick_window_start
            if self.bridge_active and dt >= 1.0:
                hz = self.tick_count / dt
                self.statusBar().showMessage(f"桥接运行中 | 实际频率 {hz:.1f} Hz")
                self.tick_count = 0
                self.tick_window_start = now
        except Exception:
            pass

    def closeEvent(self, event):
        self.stop_bridge()
        try:
            self.sg.close()
        except Exception:
            pass
        event.accept()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Haptic bridge GUI")
    parser.add_argument("--network", type=str, default=None, help="DDS network interface")
    parser.add_argument("--simulate", action="store_true", help="Use simulated SenseGlove")
    parser.add_argument("--no-robot", action="store_true", help="Use simulated robot hand")
    parser.add_argument("--bridge", type=str, default=None, help="Path to senseglove_bridge.exe")
    args = parser.parse_args()

    app = QApplication(sys.argv)

    sg_client = SenseGloveSimulator() if args.simulate else SenseGloveClient(bridge_path=args.bridge)
    sg_client.start()

    robot = FakeRobotHand() if args.no_robot else RobotHandDDS(network=args.network, lr='r')

    window = HapticBridgeWindow(robot, sg_client, simulate_robot=args.no_robot)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
