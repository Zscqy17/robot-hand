"""
Robot Hand (RH56DFTP) Standalone Test GUI

Tests the right hand via DDS:
- Subscribe to state (pos/angle/force/current) and touch sensor data
- Publish control commands (position, force, speed)
- Real-time visualization of sensor data

Usage:
    python test_robot_hand.py [--network INTERFACE]
"""

import sys
import os
import time
import threading
import numpy as np

# Add parent paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'inspire_hand_sdk'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'unitree_sdk2_python'))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QSlider, QPushButton, QGroupBox, QTabWidget,
    QStatusBar, QFrame, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from unitree_sdk2py.core.channel import (
    ChannelSubscriber, ChannelPublisher, ChannelFactoryInitialize
)
from inspire_sdkpy import inspire_hand_defaut, inspire_dds


# Finger names for the 6 DOF (robot hand order)
FINGER_NAMES = ["小拇指", "无名指", "中指", "食指", "拇指弯曲", "拇指旋转"]


class RobotHandDDS:
    """DDS communication handler for the robot hand."""
    
    def __init__(self, network=None, lr='r'):
        if network is None:
            ChannelFactoryInitialize(0)
        else:
            ChannelFactoryInitialize(0, network)
        
        self.lr = lr
        self.data_sheet = inspire_hand_defaut.data_sheet
        
        # State data
        self.states = {
            'POS_ACT': [0] * 6,
            'ANGLE_ACT': [0] * 6,
            'FORCE_ACT': [0] * 6,
            'CURRENT': [0] * 6,
            'ERROR': [0] * 6,
            'STATUS': [0] * 6,
            'TEMP': [0] * 6,
        }
        
        # Touch data (dict of var_name -> numpy array)
        self.touch = {}
        
        self._state_lock = threading.Lock()
        self._touch_lock = threading.Lock()
        
        # Subscribe to state
        self.sub_state = ChannelSubscriber(
            f"rt/inspire_hand/state/{lr}", inspire_dds.inspire_hand_state
        )
        self.sub_state.Init(self._on_state, 10)
        
        # Subscribe to touch
        self.sub_touch = ChannelSubscriber(
            f"rt/inspire_hand/touch/{lr}", inspire_dds.inspire_hand_touch
        )
        self.sub_touch.Init(self._on_touch, 10)
        
        # Publisher for control
        self.pub_ctrl = ChannelPublisher(
            f"rt/inspire_hand/ctrl/{lr}", inspire_dds.inspire_hand_ctrl
        )
        self.pub_ctrl.Init()
    
    def _on_state(self, msg: inspire_dds.inspire_hand_state):
        with self._state_lock:
            self.states = {
                'POS_ACT': list(msg.pos_act),
                'ANGLE_ACT': list(msg.angle_act),
                'FORCE_ACT': list(msg.force_act),
                'CURRENT': list(msg.current),
                'ERROR': list(msg.err),
                'STATUS': list(msg.status),
                'TEMP': list(msg.temperature),
            }
    
    def _on_touch(self, msg: inspire_dds.inspire_hand_touch):
        with self._touch_lock:
            for i, (name, addr, length, size, var) in enumerate(self.data_sheet):
                value = getattr(msg, var)
                if value is not None:
                    self.touch[var] = np.array(value).reshape(size)
    
    def get_states(self) -> dict:
        with self._state_lock:
            return dict(self.states)
    
    def get_touch(self) -> dict:
        with self._touch_lock:
            return dict(self.touch)
    
    def get_force_act(self) -> list:
        """Get current force readings for all 6 DOFs."""
        with self._state_lock:
            return list(self.states['FORCE_ACT'])
    
    def get_finger_touch_intensity(self) -> dict:
        """
        Get aggregated touch intensity per finger (0.0-1.0 range).
        Returns dict with keys: pinky, ring, middle, index, thumb, palm
        """
        with self._touch_lock:
            result = {}
            mappings = [
                ('pinky', ['fingerone_tip_touch', 'fingerone_top_touch', 'fingerone_palm_touch']),
                ('ring', ['fingertwo_tip_touch', 'fingertwo_top_touch', 'fingertwo_palm_touch']),
                ('middle', ['fingerthree_tip_touch', 'fingerthree_top_touch', 'fingerthree_palm_touch']),
                ('index', ['fingerfour_tip_touch', 'fingerfour_top_touch', 'fingerfour_palm_touch']),
                ('thumb', ['fingerfive_tip_touch', 'fingerfive_top_touch', 'fingerfive_middle_touch', 'fingerfive_palm_touch']),
                ('palm', ['palm_touch']),
            ]
            for name, vars_list in mappings:
                total = 0.0
                count = 0
                for var in vars_list:
                    if var in self.touch:
                        arr = self.touch[var].astype(float)
                        total += np.mean(arr)
                        count += 1
                # Normalize: touch sensor raw values are int16, typical range 0-1000+
                intensity = (total / max(count, 1)) / 500.0 if count > 0 else 0.0
                result[name] = min(1.0, max(0.0, intensity))
            return result
    
    def send_ctrl(self, pos_set=None, angle_set=None, force_set=None, speed_set=None):
        """Send control command to the robot hand."""
        msg = inspire_hand_defaut.get_inspire_hand_ctrl()
        if pos_set is not None:
            msg.pos_set = pos_set
        if angle_set is not None:
            msg.angle_set = angle_set
        if force_set is not None:
            msg.force_set = force_set
        if speed_set is not None:
            msg.speed_set = speed_set
        self.pub_ctrl.Write(msg)


class FingerControlWidget(QWidget):
    """Widget for controlling one finger DOF."""
    
    def __init__(self, name: str, index: int, parent=None):
        super().__init__(parent)
        self.index = index
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.name_label = QLabel(name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        layout.addWidget(self.name_label)
        
        self.slider = QSlider(Qt.Vertical)
        self.slider.setRange(0, 1000)
        self.slider.setValue(0)
        self.slider.setFixedHeight(150)
        layout.addWidget(self.slider, alignment=Qt.AlignCenter)
        
        self.value_label = QLabel("0")
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)
        
        # State display labels
        self.pos_label = QLabel("位置: --")
        self.force_label = QLabel("力: --")
        self.angle_label = QLabel("角度: --")
        for lbl in [self.pos_label, self.force_label, self.angle_label]:
            lbl.setFont(QFont("Microsoft YaHei", 8))
            layout.addWidget(lbl)
        
        self.slider.valueChanged.connect(
            lambda v: self.value_label.setText(str(v))
        )


class RobotHandTestWindow(QMainWindow):
    """Main window for robot hand testing."""
    
    def __init__(self, dds_handler: RobotHandDDS):
        super().__init__()
        self.dds = dds_handler
        self.setWindowTitle("机械手测试 - RH56DFTP 右手")
        self.setMinimumSize(900, 600)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # --- Control Section ---
        ctrl_group = QGroupBox("控制 (DDS发布)")
        ctrl_layout = QHBoxLayout(ctrl_group)
        
        self.finger_widgets = []
        for i, name in enumerate(FINGER_NAMES):
            fw = FingerControlWidget(name, i)
            ctrl_layout.addWidget(fw)
            self.finger_widgets.append(fw)
        
        # Control buttons
        btn_layout = QVBoxLayout()
        self.send_btn = QPushButton("发送位置")
        self.send_btn.clicked.connect(self.send_position)
        btn_layout.addWidget(self.send_btn)
        
        self.open_btn = QPushButton("全部张开")
        self.open_btn.clicked.connect(lambda: self._set_all_sliders(1000))
        btn_layout.addWidget(self.open_btn)
        
        self.close_btn = QPushButton("全部握紧")
        self.close_btn.clicked.connect(lambda: self._set_all_sliders(0))
        btn_layout.addWidget(self.close_btn)
        
        self.auto_send = QCheckBox("自动发送")
        self.auto_send.setChecked(False)
        btn_layout.addWidget(self.auto_send)
        
        btn_layout.addStretch()
        ctrl_layout.addLayout(btn_layout)
        main_layout.addWidget(ctrl_group)
        
        # --- State Section ---
        state_group = QGroupBox("状态 (DDS订阅)")
        state_layout = QGridLayout(state_group)
        
        # Force display
        state_layout.addWidget(QLabel("力反馈:"), 0, 0)
        self.force_labels = []
        for i, name in enumerate(FINGER_NAMES):
            lbl = QLabel(f"{name}: --")
            lbl.setFont(QFont("Microsoft YaHei", 9))
            state_layout.addWidget(lbl, 0, i + 1)
            self.force_labels.append(lbl)
        
        # Touch intensity
        state_layout.addWidget(QLabel("触觉强度:"), 1, 0)
        self.touch_labels = {}
        touch_names = ["pinky", "ring", "middle", "index", "thumb", "palm"]
        touch_cn = ["小拇指", "无名指", "中指", "食指", "拇指", "手掌"]
        for i, (en, cn) in enumerate(zip(touch_names, touch_cn)):
            lbl = QLabel(f"{cn}: --")
            lbl.setFont(QFont("Microsoft YaHei", 9))
            state_layout.addWidget(lbl, 1, i + 1)
            self.touch_labels[en] = lbl
        
        main_layout.addWidget(state_group)
        
        # Status bar
        self.statusBar().showMessage("等待DDS数据...")
        
        # Timer for periodic updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(50)  # 20 Hz
    
    def _set_all_sliders(self, value):
        for fw in self.finger_widgets:
            fw.slider.setValue(value)
    
    def send_position(self):
        pos = [fw.slider.value() for fw in self.finger_widgets]
        self.dds.send_ctrl(pos_set=pos)
        self.statusBar().showMessage(f"已发送位置: {pos}")
    
    def update_display(self):
        # Auto-send if enabled
        if self.auto_send.isChecked():
            self.send_position()
        
        # Update state
        states = self.dds.get_states()
        for i, fw in enumerate(self.finger_widgets):
            fw.pos_label.setText(f"位置: {states['POS_ACT'][i]}")
            fw.force_label.setText(f"力: {states['FORCE_ACT'][i]}")
            fw.angle_label.setText(f"角度: {states['ANGLE_ACT'][i]}")
        
        # Update force labels
        for i, lbl in enumerate(self.force_labels):
            lbl.setText(f"{FINGER_NAMES[i]}: {states['FORCE_ACT'][i]}")
        
        # Update touch intensity
        touch_intensity = self.dds.get_finger_touch_intensity()
        for name, lbl in self.touch_labels.items():
            val = touch_intensity.get(name, 0.0)
            cn = lbl.text().split(":")[0]
            lbl.setText(f"{cn}: {val:.2f}")
        
        self.statusBar().showMessage(
            f"状态更新 | 温度: {states['TEMP']} | 电流: {states['CURRENT']}"
        )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Robot Hand Test GUI")
    parser.add_argument("--network", type=str, default=None, 
                        help="Network interface for DDS")
    args = parser.parse_args()
    
    app = QApplication(sys.argv)
    
    dds = RobotHandDDS(network=args.network, lr='r')
    window = RobotHandTestWindow(dds)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
