"""
SenseGlove Standalone Test GUI

Tests the SenseGlove (right hand) via the C++ bridge:
- Connection status display
- Force feedback test (per-finger sliders)
- Vibration test (per-location controls)
- Custom waveform test
- Wrist squeeze test

Usage:
    python test_senseglove.py [--simulate]
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QSlider, QPushButton, QGroupBox, QStatusBar,
    QDoubleSpinBox, QComboBox, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette

from senseglove_client import (
    SenseGloveClient, SenseGloveSimulator, EHapticLocation, SenseGloveFinger
)


FINGER_NAMES = ["拇指", "食指", "中指", "无名指", "小拇指"]

HAPTIC_LOCATIONS = [
    ("拇指尖", EHapticLocation.ThumbTip),
    ("食指尖", EHapticLocation.IndexTip),
    ("中指尖", EHapticLocation.MiddleTip),
    ("无名指尖", EHapticLocation.RingTip),
    ("小拇指尖", EHapticLocation.PinkyTip),
    ("掌心(食指侧)", EHapticLocation.PalmIndexSide),
    ("掌心(小指侧)", EHapticLocation.PalmPinkySide),
    ("整只手", EHapticLocation.WholeHand),
]


class FFBSlider(QWidget):
    """Force feedback slider for one finger."""
    
    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.label = QLabel(name)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        layout.addWidget(self.label)
        
        self.slider = QSlider(Qt.Vertical)
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        self.slider.setFixedHeight(120)
        layout.addWidget(self.slider, alignment=Qt.AlignCenter)
        
        self.value_label = QLabel("0%")
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)
        
        self.slider.valueChanged.connect(
            lambda v: self.value_label.setText(f"{v}%")
        )
    
    @property
    def value(self) -> float:
        return self.slider.value() / 100.0


class SenseGloveTestWindow(QMainWindow):
    """Main window for SenseGlove testing."""
    
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.setWindowTitle("SenseGlove 测试 - 右手")
        self.setMinimumSize(800, 650)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # --- Connection Status ---
        status_group = QGroupBox("连接状态")
        status_layout = QGridLayout(status_group)
        
        self.status_labels = {}
        labels = [
            ("running", "Bridge状态:", 0, 0),
            ("version", "库版本:", 0, 2),
            ("sensecom", "SenseCom:", 1, 0),
            ("connected", "右手连接:", 1, 2),
            ("type", "设备类型:", 2, 0),
            ("features", "支持功能:", 2, 2),
        ]
        for key, text, row, col in labels:
            lbl = QLabel(text)
            lbl.setFont(QFont("Microsoft YaHei", 9))
            val = QLabel("--")
            val.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
            status_layout.addWidget(lbl, row, col)
            status_layout.addWidget(val, row, col + 1)
            self.status_labels[key] = val
        
        self.refresh_btn = QPushButton("刷新状态")
        self.refresh_btn.clicked.connect(self.refresh_status)
        status_layout.addWidget(self.refresh_btn, 3, 0, 1, 4)
        
        main_layout.addWidget(status_group)
        
        # --- Force Feedback ---
        ffb_group = QGroupBox("力反馈 (Force Feedback)")
        ffb_layout = QHBoxLayout(ffb_group)
        
        self.ffb_sliders = []
        for name in FINGER_NAMES:
            s = FFBSlider(name)
            ffb_layout.addWidget(s)
            self.ffb_sliders.append(s)
        
        ffb_btn_layout = QVBoxLayout()
        self.ffb_send_btn = QPushButton("发送力反馈")
        self.ffb_send_btn.clicked.connect(self.send_ffb)
        ffb_btn_layout.addWidget(self.ffb_send_btn)
        
        self.ffb_all_btn = QPushButton("全部100%")
        self.ffb_all_btn.clicked.connect(lambda: self._set_all_ffb(100))
        ffb_btn_layout.addWidget(self.ffb_all_btn)
        
        self.ffb_clear_btn = QPushButton("全部归零")
        self.ffb_clear_btn.clicked.connect(lambda: self._set_all_ffb(0))
        ffb_btn_layout.addWidget(self.ffb_clear_btn)
        
        ffb_btn_layout.addStretch()
        ffb_layout.addLayout(ffb_btn_layout)
        main_layout.addWidget(ffb_group)
        
        # --- Vibration ---
        vibro_group = QGroupBox("振动 (Custom Waveform)")
        vibro_layout = QGridLayout(vibro_group)
        
        vibro_layout.addWidget(QLabel("位置:"), 0, 0)
        self.vibro_location = QComboBox()
        for name, loc in HAPTIC_LOCATIONS:
            self.vibro_location.addItem(name, loc)
        vibro_layout.addWidget(self.vibro_location, 0, 1)
        
        vibro_layout.addWidget(QLabel("强度:"), 0, 2)
        self.vibro_amplitude = QDoubleSpinBox()
        self.vibro_amplitude.setRange(0.0, 1.0)
        self.vibro_amplitude.setSingleStep(0.1)
        self.vibro_amplitude.setValue(1.0)
        vibro_layout.addWidget(self.vibro_amplitude, 0, 3)
        
        vibro_layout.addWidget(QLabel("持续(秒):"), 1, 0)
        self.vibro_duration = QDoubleSpinBox()
        self.vibro_duration.setRange(0.01, 5.0)
        self.vibro_duration.setSingleStep(0.05)
        self.vibro_duration.setValue(0.2)
        vibro_layout.addWidget(self.vibro_duration, 1, 1)
        
        vibro_layout.addWidget(QLabel("频率(Hz):"), 1, 2)
        self.vibro_frequency = QDoubleSpinBox()
        self.vibro_frequency.setRange(1.0, 500.0)
        self.vibro_frequency.setSingleStep(10.0)
        self.vibro_frequency.setValue(80.0)
        vibro_layout.addWidget(self.vibro_frequency, 1, 3)
        
        self.vibro_send_btn = QPushButton("发送振动")
        self.vibro_send_btn.clicked.connect(self.send_vibration)
        vibro_layout.addWidget(self.vibro_send_btn, 2, 0, 1, 4)
        
        main_layout.addWidget(vibro_group)
        
        # --- Wrist Squeeze ---
        squeeze_group = QGroupBox("腕部挤压 (Wrist Squeeze, Nova 2.0)")
        squeeze_layout = QHBoxLayout(squeeze_group)
        
        squeeze_layout.addWidget(QLabel("挤压强度:"))
        self.squeeze_slider = QSlider(Qt.Horizontal)
        self.squeeze_slider.setRange(0, 100)
        self.squeeze_slider.setValue(0)
        squeeze_layout.addWidget(self.squeeze_slider)
        
        self.squeeze_label = QLabel("0%")
        squeeze_layout.addWidget(self.squeeze_label)
        self.squeeze_slider.valueChanged.connect(
            lambda v: self.squeeze_label.setText(f"{v}%")
        )
        
        self.squeeze_send_btn = QPushButton("发送")
        self.squeeze_send_btn.clicked.connect(self.send_squeeze)
        squeeze_layout.addWidget(self.squeeze_send_btn)
        
        main_layout.addWidget(squeeze_group)
        
        # --- Stop All ---
        self.stop_btn = QPushButton("⬛ 停止所有触觉反馈")
        self.stop_btn.setStyleSheet("background-color: #cc3333; color: white; font-size: 14px; padding: 8px;")
        self.stop_btn.clicked.connect(self.stop_all)
        main_layout.addWidget(self.stop_btn)
        
        # Status bar
        self.statusBar().showMessage("正在初始化...")
        
        # Initial status check
        QTimer.singleShot(500, self.refresh_status)
    
    def _set_all_ffb(self, value):
        for s in self.ffb_sliders:
            s.slider.setValue(value)
    
    def refresh_status(self):
        # Init
        init_resp = self.client.init()
        if init_resp.get("ok"):
            self.status_labels["running"].setText("✅ 运行中")
            self.status_labels["version"].setText(init_resp.get("version", "?"))
            sensecom = init_resp.get("sensecom", False)
            self.status_labels["sensecom"].setText("✅ 运行" if sensecom else "❌ 未运行")
        else:
            self.status_labels["running"].setText("❌ 错误")
            self.statusBar().showMessage(f"初始化失败: {init_resp.get('error', '?')}")
            return
        
        # Status
        status = self.client.get_status()
        if status.get("ok"):
            connected = status.get("right_connected", False)
            self.status_labels["connected"].setText("✅ 已连接" if connected else "❌ 未连接")
            self.status_labels["type"].setText(status.get("type", "?"))
            
            features = []
            if status.get("supports_waveform"):
                features.append("波形振动")
            if status.get("supports_wrist_squeeze"):
                features.append("腕部挤压")
            self.status_labels["features"].setText(", ".join(features) if features else "无")
            
            self.statusBar().showMessage(
                f"检测到 {status.get('gloves', 0)} 个手套"
            )
    
    def send_ffb(self):
        levels = [s.value for s in self.ffb_sliders]
        resp = self.client.set_force_feedback(levels)
        if resp.get("ok"):
            self.statusBar().showMessage(f"力反馈已发送: {[f'{v:.0%}' for v in levels]}")
        else:
            self.statusBar().showMessage(f"力反馈失败: {resp.get('error', '?')}")
    
    def send_vibration(self):
        location = self.vibro_location.currentData()
        amplitude = self.vibro_amplitude.value()
        duration = self.vibro_duration.value()
        frequency = self.vibro_frequency.value()
        
        resp = self.client.send_waveform(amplitude, duration, frequency, location)
        if resp.get("ok"):
            self.statusBar().showMessage(
                f"振动已发送: {self.vibro_location.currentText()} "
                f"A={amplitude:.1f} D={duration:.2f}s F={frequency:.0f}Hz"
            )
        else:
            self.statusBar().showMessage(f"振动失败: {resp.get('error', '?')}")
    
    def send_squeeze(self):
        level = self.squeeze_slider.value() / 100.0
        resp = self.client.set_wrist_squeeze(level)
        if resp.get("ok"):
            self.statusBar().showMessage(f"腕部挤压: {level:.0%}")
        else:
            self.statusBar().showMessage(f"腕部挤压失败: {resp.get('error', '?')}")
    
    def stop_all(self):
        self._set_all_ffb(0)
        self.squeeze_slider.setValue(0)
        resp = self.client.stop_haptics()
        if resp.get("ok"):
            self.statusBar().showMessage("所有触觉反馈已停止")
        else:
            self.statusBar().showMessage(f"停止失败: {resp.get('error', '?')}")
    
    def closeEvent(self, event):
        self.client.stop_haptics()
        self.client.close()
        event.accept()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SenseGlove Test GUI")
    parser.add_argument("--simulate", action="store_true", 
                        help="Use simulated SenseGlove (no hardware)")
    parser.add_argument("--bridge", type=str, default=None,
                        help="Path to senseglove_bridge.exe")
    args = parser.parse_args()
    
    app = QApplication(sys.argv)
    
    if args.simulate:
        client = SenseGloveSimulator()
    else:
        client = SenseGloveClient(bridge_path=args.bridge)
    
    client.start()
    
    window = SenseGloveTestWindow(client)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
