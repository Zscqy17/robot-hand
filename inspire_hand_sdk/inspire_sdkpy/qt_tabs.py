import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QGridLayout,
                              QLabel, QVBoxLayout, QHBoxLayout, QSlider, QPushButton, QGroupBox,
                              QSpinBox, QFormLayout, QScrollArea, QFrame, QSplitter, QLineEdit,
                              QInputDialog)
from PyQt5.QtCore import Qt
from .inspire_hand_defaut import *
import colorcet  # 确保安装 colorcet 库
import numpy as np
import json
import os
import time

class ImageTab(QWidget):
    def __init__(self,datas=data_sheet):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)  
        
        self.grid_layout=QGridLayout()   
        self.layout.addLayout(self.grid_layout)   
        self.data_sheet=datas
        
        self.create_images()

    def create_images(self):
        num_cols = 4  # 每行的列数
        num_rows = (len(data_sheet) + num_cols - 1) // num_cols  # 计算行数
        self.plots = []
        self.color_maps = []
        self.color_bars = []
        for i, (name, addr, length, size, var) in enumerate(self.data_sheet):
                
            row = i // num_cols  # 计算当前行
            col = i % num_cols  # 计算当前列            # 创建随机大小的图像数据
            # width = random.randint(50, 100)
            # height = random.randint(50, 150)
            # image_data = np.random.rand(height, width)  # 生成二维图像数据

            # 创建图形布局窗口
            layout_widget = pg.GraphicsLayoutWidget(show=True)
            plot_item = layout_widget.addPlot(row=0, col=0)
            # 为图块设置名字
            plot_item.setTitle(name)
            img_item = pg.ImageItem(np.random.rand(size[0],size[1]))
            plot_item.addItem(img_item)
            self.plots.append(img_item)

            # 创建颜色映射
            color_map = pg.ColorMap(pos=np.linspace(0, 1, 256), color=colorcet.fire[:256])
            self.color_maps.append(color_map)

            # 创建颜色条
            color_bar = pg.ColorBarItem(colorMap=color_map, values=(0, 1), width=5, orientation='h')
            self.color_bars.append(color_bar)
            layout_widget.addItem(color_bar, row=1, col=0)

            # 将图形布局添加到网格
            self.grid_layout.addWidget(layout_widget, row, col)
    def update_plot(self,data_dict):
        for i, (name, addr, length, size,var) in enumerate(self.data_sheet):
            self.plots[i].setImage(data_dict[var], autoLevels=True)  # 更新图像数据
            max_val = np.max(data_dict[var])
            self.plots[i].setLevels((0, max_val))  # 设置图像颜色范围
            # 更新颜色条
            self.color_bars[i].setLevels((0, max_val))  # 更新颜色条的范围
            self.plots[i].setColorMap(self.color_maps[i])  # 设置颜色映射

class CurveTab(QWidget):
    def __init__(self,datas=data_sheet,history_len=100):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)  
        
        self.grid_layout=QGridLayout()   
        self.layout.addLayout(self.grid_layout)   
        self.data_sheet=datas
        self.history_length = history_len
        self.history = {
        'POS_ACT': [np.zeros(history_len) for _ in range(6)],   # 6 个数据点
        'ANGLE_ACT': [np.zeros(history_len) for _ in range(6)], # 6 个数据点
        'FORCE_ACT': [np.zeros(history_len) for _ in range(6)], # 6 个数据点
        'CURRENT': [np.zeros(history_len) for _ in range(6)],   # 6 个数据点
        'ERROR': [np.zeros(history_len) for _ in range(6)],     # 6 个数据点
        'STATUS': [np.zeros(history_len) for _ in range(6)],    # 6 个数据点
        'TEMP': [np.zeros(history_len) for _ in range(6)]       # 6 个数据点
        }
        self.create_curves()
        

    def create_curves(self):
        self.error_label = QLabel("ERROR: ")
        self.status_label = QLabel("STATUS: ")
        
        self.layout.addWidget(self.error_label)  # 添加ERROR标签
        self.layout.addWidget(self.status_label)  # 添加STATUS标签
        
        self.plot_items = {name: pg.PlotWidget() for name in ['POS_ACT', 'ANGLE_ACT', 'FORCE_ACT', 'CURRENT', 'ERROR', 'STATUS', 'TEMP']}
        for i, (name, plot_widget) in enumerate(self.plot_items.items()):
                self.grid_layout.addWidget(plot_widget, i // 2, i % 2)  # 每行两个图
                plot_widget.setTitle(name)
                plot_widget.setLabel('left', 'Y-axis')
                plot_widget.setLabel('bottom', 'X-axis')
                plot_widget.setBackground((0, 0, 0))
                plot_widget.addLegend()
                plot_widget.showButtons()
                plot_widget.enableAutoRange()
                plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.curves = {
                'POS_ACT': [self.plot_items['POS_ACT'].plot(pen=pg.mkPen(color),name=f'POS_ACT {i + 1}') for i, color in enumerate(colorcet.glasbey[:6])],
                'ANGLE_ACT': [self.plot_items['ANGLE_ACT'].plot(pen=pg.mkPen(color),name=f'ANGLE_ACT {i + 1}') for i, color in enumerate(colorcet.glasbey[:6])],
                'FORCE_ACT': [self.plot_items['FORCE_ACT'].plot(pen=pg.mkPen(color),name=f'FORCE_ACT {i + 1}') for i, color in enumerate(colorcet.glasbey[:6])],
                'CURRENT': [self.plot_items['CURRENT'].plot(pen=pg.mkPen(color),name=f'CURRENT {i + 1}') for i, color in enumerate(colorcet.glasbey[:6])],
                'ERROR': [self.plot_items['ERROR'].plot(pen=pg.mkPen(color),name=f'ERROR {i + 1}') for i, color in enumerate(colorcet.glasbey[:6])],  
                'STATUS': [self.plot_items['STATUS'].plot(pen=pg.mkPen(color),name=f'STATUS {i + 1}') for i, color in enumerate(colorcet.glasbey[:6])],  
                'TEMP': [self.plot_items['TEMP'].plot(pen=pg.mkPen(color),name=f'TEMP {i + 1}') for i, color in enumerate(colorcet.glasbey[:6])] 
            }
    #   data_dict = {
    #     'POS_ACT': POS_ACT,
    #     'ANGLE_ACT': ANGLE_ACT,
    #     'FORCE_ACT': FORCE_ACT,
    #     'CURRENT': CURRENT,
    #     'ERROR': ERROR,
    #     'STATUS': STATUS,
    #     'TEMP': TEMP
    # }
    def update_plot(self,data_dict):
        # 更新每个曲线的数据
        try:
            # 更新每个曲线的数据
            for category, datas in data_dict.items():
                if datas is not None:
                    for i in range(len(datas)):
                        # 追加新的数据点到历史记录，并移除最老的数据点
                        self.history[category][i] = np.roll(self.history[category][i], -1)
                        self.history[category][i][-1] = datas[i]
                        # 更新曲线
                        self.curves[category][i].setData(self.history[category][i])
                else:
                    raise ValueError(f"Data for category '{category}' is None")

            err = update_error_label(data_dict['ERROR'])
            self.error_label.setText(err)
            self.status_label.setText("STATUS: " + ', '.join(['%s' % status_codes[s] for s in data_dict['STATUS']]))

        except Exception as e:
            print(f"Error updating plot: {e}")  # 打印具体的错误信息
            print(f"Data received: {data_dict}")  # 打印接收到的数据以便调试
            raise RuntimeError(f"Failed to update plot due to: {e}")
  
FINGER_NAMES = ['小拇指', '无名指', '中指', '食指', '大拇指弯曲', '大拇指旋转']
FINGER_COLORS = ['#e6194b', '#f58231', '#3cb44b', '#4363d8', '#911eb4', '#f032e6']

DEFAULT_GESTURES = {
    '张开': [1000, 1000, 1000, 1000, 1000, 1000],
    '握拳': [0, 0, 0, 0, 0, 0],
    '二指捏': [1000, 1000, 1000, 0, 0, 0],
    '三指捏': [1000, 1000, 0, 0, 0, 0],
    '竖大拇指': [0, 0, 0, 0, 1000, 1000],
    '食指指向': [0, 0, 0, 1000, 0, 0],
    '半握': [500, 500, 500, 500, 500, 500],
}

GESTURE_FILE = os.path.join(os.path.dirname(__file__), 'gestures.json')

def load_gestures():
    if os.path.exists(GESTURE_FILE):
        try:
            with open(GESTURE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # convert to list of (name, angles) to preserve order
                return [(item['name'], item['angles']) for item in data]
        except Exception:
            pass
    return [(k, list(v)) for k, v in DEFAULT_GESTURES.items()]

def save_gestures(gesture_list):
    data = [{'name': name, 'angles': angles} for name, angles in gesture_list]
    with open(GESTURE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class ControlTab(QWidget):
    def __init__(self, data_handler):
        super().__init__()
        self.data_handler = data_handler
        self.gestures = load_gestures()  # list of (name, angles)
        self.editing = False
        self.edit_target_idx = None  # 当前编辑的手势索引

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.main_layout = QVBoxLayout(container)
        scroll.setWidget(container)

        outer = QVBoxLayout()
        outer.addWidget(scroll)
        self.setLayout(outer)

        # === 手势预设区域 ===
        self.gesture_group = QGroupBox("手势预设 (角度模式)")
        gesture_outer = QVBoxLayout()

        # 手势按钮行
        self.gesture_btn_layout = QHBoxLayout()
        self.gesture_buttons = []
        self._rebuild_gesture_buttons()
        gesture_outer.addLayout(self.gesture_btn_layout)

        # 编辑/新增/删除 按钮行
        edit_row = QHBoxLayout()
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.setMinimumHeight(32)
        self.edit_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        self.edit_btn.clicked.connect(self._toggle_edit_mode)

        self.add_btn = QPushButton("+ 新增手势")
        self.add_btn.setMinimumHeight(32)
        self.add_btn.clicked.connect(self._add_gesture)
        self.add_btn.setVisible(False)

        self.del_btn = QPushButton("- 删除选中")
        self.del_btn.setMinimumHeight(32)
        self.del_btn.setStyleSheet("color: #f44336;")
        self.del_btn.clicked.connect(self._delete_gesture)
        self.del_btn.setVisible(False)

        self.edit_hint = QLabel("")
        self.edit_hint.setStyleSheet("color: #FF9800; font-size: 12px;")

        edit_row.addWidget(self.edit_btn)
        edit_row.addWidget(self.add_btn)
        edit_row.addWidget(self.del_btn)
        edit_row.addWidget(self.edit_hint)
        edit_row.addStretch()
        gesture_outer.addLayout(edit_row)

        self.gesture_group.setLayout(gesture_outer)
        self.main_layout.addWidget(self.gesture_group)

        # === 主控制滑块 ===
        self.slider_group = QGroupBox("角度控制 ANGLE_SET (0=弯曲, 1000=张开)")
        slider_form = QGridLayout()
        self.sliders = []
        self.slider_labels = []
        for i, name in enumerate(FINGER_NAMES):
            label = QLabel(f"{name}:")
            label.setStyleSheet(f"color: {FINGER_COLORS[i]}; font-weight: bold;")
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 1000)
            slider.setValue(1000)
            slider.setMinimumWidth(300)
            val_label = QLabel("1000")
            val_label.setMinimumWidth(50)
            slider.valueChanged.connect(lambda v, lbl=val_label: lbl.setText(str(v)))
            slider_form.addWidget(label, i, 0)
            slider_form.addWidget(slider, i, 1)
            slider_form.addWidget(val_label, i, 2)
            self.sliders.append(slider)
            self.slider_labels.append(val_label)

        send_btn = QPushButton("发 送")
        send_btn.setMinimumHeight(40)
        send_btn.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px; font-weight: bold;")
        send_btn.clicked.connect(self.send_main)
        slider_form.addWidget(send_btn, len(FINGER_NAMES), 0, 1, 3)
        self.slider_group.setLayout(slider_form)
        self.main_layout.addWidget(self.slider_group)

        # === 力控+速度 单行 ===
        params_layout = QHBoxLayout()

        force_group = QGroupBox("力控阈值 FORCE_SET (0-3000g)")
        force_form = QGridLayout()
        self.force_spins = []
        for i, name in enumerate(FINGER_NAMES):
            label = QLabel(f"{name}:")
            spin = QSpinBox()
            spin.setRange(0, 3000)
            spin.setValue(500)
            spin.setSingleStep(50)
            force_form.addWidget(label, i, 0)
            force_form.addWidget(spin, i, 1)
            self.force_spins.append(spin)
        send_force_btn = QPushButton("发送力控")
        send_force_btn.setMinimumHeight(36)
        send_force_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        send_force_btn.clicked.connect(self.send_forces)
        force_form.addWidget(send_force_btn, len(FINGER_NAMES), 0, 1, 2)
        force_group.setLayout(force_form)
        params_layout.addWidget(force_group)

        speed_group = QGroupBox("速度设置 SPEED_SET (0-1000)")
        speed_form = QVBoxLayout()
        for lbl_text, default_val in [("全局速度:", 500)]:
            row = QHBoxLayout()
            row.addWidget(QLabel(lbl_text))
            self.speed_spin = QSpinBox()
            self.speed_spin.setRange(0, 1000)
            self.speed_spin.setValue(default_val)
            self.speed_spin.setSingleStep(50)
            row.addWidget(self.speed_spin)
            speed_form.addLayout(row)
        send_speed_btn = QPushButton("发送速度")
        send_speed_btn.setMinimumHeight(36)
        send_speed_btn.clicked.connect(self.send_speed)
        speed_form.addWidget(send_speed_btn)
        speed_form.addStretch()
        speed_group.setLayout(speed_form)
        params_layout.addWidget(speed_group)

        self.main_layout.addLayout(params_layout)

        # === 实时控制 ===
        self.realtime_btn = QPushButton("实时控制模式: 关闭")
        self.realtime_btn.setCheckable(True)
        self.realtime_btn.setMinimumHeight(40)
        self.realtime_btn.setStyleSheet("background-color: #666; color: white; font-weight: bold; font-size: 13px;")
        self.realtime_btn.toggled.connect(self.toggle_realtime)
        self.main_layout.addWidget(self.realtime_btn)
        self.realtime = False

    # --- 手势按钮管理 ---
    def _rebuild_gesture_buttons(self):
        # 清空旧按钮
        while self.gesture_btn_layout.count():
            item = self.gesture_btn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.gesture_buttons = []
        for idx, (name, angles) in enumerate(self.gestures):
            btn = QPushButton(name)
            btn.setMinimumHeight(36)
            btn.clicked.connect(lambda checked, i=idx: self._gesture_clicked(i))
            self.gesture_btn_layout.addWidget(btn)
            self.gesture_buttons.append(btn)

    def _gesture_clicked(self, idx):
        if self.editing:
            # 编辑模式: 选中该手势进行编辑
            self.edit_target_idx = idx
            name, angles = self.gestures[idx]
            # 高亮选中按钮
            for i, btn in enumerate(self.gesture_buttons):
                if i == idx:
                    btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; border: 2px solid #E65100;")
                else:
                    btn.setStyleSheet("")
            # 加载角度到滑块
            for i, a in enumerate(angles):
                self.sliders[i].setValue(a)
            self.edit_hint.setText(f"正在编辑: [{name}]  — 调整滑块后点击「完成」保存，双击按钮可改名")
        else:
            # 正常模式: 发送手势
            _, angles = self.gestures[idx]
            self.send_gesture(angles)

    def _toggle_edit_mode(self):
        if not self.editing:
            # 进入编辑模式
            self.editing = True
            self.edit_target_idx = None
            self.edit_btn.setText("完成")
            self.edit_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            self.add_btn.setVisible(True)
            self.del_btn.setVisible(True)
            self.edit_hint.setText("点击手势按钮选中编辑，双击按钮改名，调整滑块设定角度")
            # 给按钮加双击改名
            for i, btn in enumerate(self.gesture_buttons):
                btn.installEventFilter(self)
        else:
            # 完成编辑 — 保存当前选中的手势
            if self.edit_target_idx is not None:
                idx = self.edit_target_idx
                old_name = self.gestures[idx][0]
                new_angles = [s.value() for s in self.sliders]
                self.gestures[idx] = (old_name, new_angles)
            save_gestures(self.gestures)
            # 退出编辑模式
            self.editing = False
            self.edit_target_idx = None
            self.edit_btn.setText("编辑")
            self.edit_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
            self.add_btn.setVisible(False)
            self.del_btn.setVisible(False)
            self.edit_hint.setText("已保存")
            for btn in self.gesture_buttons:
                btn.setStyleSheet("")
                btn.removeEventFilter(self)
            self._rebuild_gesture_buttons()
            QtCore.QTimer.singleShot(2000, lambda: self.edit_hint.setText(""))

    def eventFilter(self, obj, event):
        if self.editing and event.type() == QtCore.QEvent.MouseButtonDblClick:
            # 双击改名
            for i, btn in enumerate(self.gesture_buttons):
                if obj is btn:
                    old_name = self.gestures[i][0]
                    new_name, ok = QInputDialog.getText(self, "重命名手势", "手势名称:", text=old_name)
                    if ok and new_name.strip():
                        self.gestures[i] = (new_name.strip(), self.gestures[i][1])
                        btn.setText(new_name.strip())
                    return True
        return super().eventFilter(obj, event)

    def _add_gesture(self):
        new_name, ok = QInputDialog.getText(self, "新增手势", "手势名称:")
        if ok and new_name.strip():
            angles = [s.value() for s in self.sliders]
            self.gestures.append((new_name.strip(), angles))
            save_gestures(self.gestures)
            self._rebuild_gesture_buttons()
            # 重新安装事件过滤器
            for btn in self.gesture_buttons:
                btn.installEventFilter(self)
            self.edit_hint.setText(f"已新增: [{new_name.strip()}]")

    def _delete_gesture(self):
        if self.edit_target_idx is not None:
            name = self.gestures[self.edit_target_idx][0]
            del self.gestures[self.edit_target_idx]
            self.edit_target_idx = None
            save_gestures(self.gestures)
            self._rebuild_gesture_buttons()
            for btn in self.gesture_buttons:
                btn.installEventFilter(self)
            self.edit_hint.setText(f"已删除: [{name}]")

    # --- 实时控制 ---
    def toggle_realtime(self, checked):
        self.realtime = checked
        if checked:
            self.realtime_btn.setText("实时控制模式: 开启 (拖动滑块自动发送)")
            self.realtime_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; font-size: 13px;")
            for slider in self.sliders:
                slider.valueChanged.connect(self._realtime_send)
        else:
            self.realtime_btn.setText("实时控制模式: 关闭")
            self.realtime_btn.setStyleSheet("background-color: #666; color: white; font-weight: bold; font-size: 13px;")
            for slider in self.sliders:
                try:
                    slider.valueChanged.disconnect(self._realtime_send)
                except TypeError:
                    pass

    def _realtime_send(self, _=None):
        if self.realtime:
            self.send_main()

    def send_gesture(self, angles):
        for i, a in enumerate(angles):
            self.sliders[i].setValue(a)
        if not self.realtime:
            self.send_main()

    def send_main(self):
        values = [s.value() for s in self.sliders]
        try:
            self.data_handler.set_angle(values)
        except Exception as e:
            print(f"发送失败: {e}")

    def send_forces(self):
        forces = [s.value() for s in self.force_spins]
        try:
            self.data_handler.set_force(forces)
        except Exception as e:
            print(f"发送力控失败: {e}")

    def send_speed(self):
        speeds = [self.speed_spin.value()] * 6
        try:
            self.data_handler.set_speed(speeds)
        except Exception as e:
            print(f"发送速度失败: {e}")


class ForceVisualizationTab(QWidget):
    """实时力度/触觉柱状图可视化"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        # --- 力度柱状图 ---
        self.force_plot = pg.PlotWidget(title="各手指实际受力 FORCE_ACT (g)")
        self.force_plot.setLabel('left', '力度 (g)')
        self.force_plot.setLabel('bottom', '')
        self.force_plot.setBackground('#1e1e1e')
        self.force_plot.showGrid(y=True, alpha=0.3)
        self.force_plot.setYRange(-500, 3000)

        self.force_bars = pg.BarGraphItem(
            x=list(range(6)), height=[0]*6, width=0.6,
            brushes=[pg.mkBrush(c) for c in FINGER_COLORS]
        )
        self.force_plot.addItem(self.force_bars)

        ax = self.force_plot.getAxis('bottom')
        ax.setTicks([[(i, FINGER_NAMES[i]) for i in range(6)]])
        layout.addWidget(self.force_plot)

        # --- 力度数值标签 ---
        self.force_value_layout = QHBoxLayout()
        self.force_value_labels = []
        for i, name in enumerate(FINGER_NAMES):
            frame = QFrame()
            frame.setStyleSheet(f"background-color: {FINGER_COLORS[i]}; border-radius: 6px;")
            frame_layout = QVBoxLayout(frame)
            name_label = QLabel(name)
            name_label.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
            name_label.setAlignment(Qt.AlignCenter)
            val_label = QLabel("0 g")
            val_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
            val_label.setAlignment(Qt.AlignCenter)
            frame_layout.addWidget(name_label)
            frame_layout.addWidget(val_label)
            self.force_value_layout.addWidget(frame)
            self.force_value_labels.append(val_label)
        layout.addLayout(self.force_value_layout)

        # --- 电流柱状图 ---
        self.current_plot = pg.PlotWidget(title="各驱动器电流 CURRENT (mA)")
        self.current_plot.setLabel('left', '电流 (mA)')
        self.current_plot.setBackground('#1e1e1e')
        self.current_plot.showGrid(y=True, alpha=0.3)
        self.current_plot.setYRange(0, 2000)

        self.current_bars = pg.BarGraphItem(
            x=list(range(6)), height=[0]*6, width=0.6,
            brushes=[pg.mkBrush(c) for c in FINGER_COLORS]
        )
        self.current_plot.addItem(self.current_bars)
        ax2 = self.current_plot.getAxis('bottom')
        ax2.setTicks([[(i, FINGER_NAMES[i]) for i in range(6)]])
        layout.addWidget(self.current_plot)

        # --- 温度 ---
        self.temp_layout = QHBoxLayout()
        self.temp_labels = []
        for i, name in enumerate(FINGER_NAMES):
            lbl = QLabel(f"{name}: --°C")
            lbl.setStyleSheet("font-size: 12px; padding: 4px;")
            lbl.setAlignment(Qt.AlignCenter)
            self.temp_layout.addWidget(lbl)
            self.temp_labels.append(lbl)
        layout.addLayout(self.temp_layout)

    def update_data(self, states):
        force = states.get('FORCE_ACT')
        if force is not None:
            self.force_bars.setOpts(height=list(force))
            for i, v in enumerate(force):
                self.force_value_labels[i].setText(f"{v} g")

        current = states.get('CURRENT')
        if current is not None:
            self.current_bars.setOpts(height=list(current))

        temp = states.get('TEMP')
        if temp is not None:
            for i, t in enumerate(temp):
                self.temp_labels[i].setText(f"{FINGER_NAMES[i]}: {t}°C")


class MainWindow(QMainWindow):
    def __init__(self, data_handler, data=data_sheet,dt=100,name="Qt with PyQtGraph",Plot_touch=True,run_time=False):
        super().__init__()
        self.setWindowTitle(name)
        self.setGeometry(50, 50, 1600, 900)
        self.dt=dt
        self.data_handler = data_handler
        self.Plot_touch_=Plot_touch
        self.run_time=run_time
        self.touch_counter = 0
        self.touch_interval = 5

        # --- 创建各面板 ---
        self.control_tab = ControlTab(data_handler)
        self.force_viz_tab = ForceVisualizationTab()
        self.curve_tab = CurveTab(data)

        # --- 左侧: 控制面板 ---
        left_panel = self.control_tab

        # --- 右侧: 上下分栏 力度可视化 + 曲线/触觉 ---
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.addWidget(self.force_viz_tab)

        if Plot_touch:
            self.image_tab = ImageTab(data)
            right_tabs = QTabWidget()
            right_tabs.addTab(self.curve_tab, "Curves")
            right_tabs.addTab(self.image_tab, "Touch Sensors")
            right_splitter.addWidget(right_tabs)
        else:
            right_splitter.addWidget(self.curve_tab)

        right_splitter.setStretchFactor(0, 2)
        right_splitter.setStretchFactor(1, 3)

        # --- 主分栏: 左控制 | 右数据 ---
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([700, 900])

        self.setCentralWidget(main_splitter)
        
    def update_plot(self):
        start_time = time.time()
        read_touch = False
        if self.Plot_touch_:
            self.touch_counter += 1
            if self.touch_counter >= self.touch_interval:
                self.touch_counter = 0
                read_touch = True
        data_dict = self.data_handler.read(read_touch=read_touch)
        self.curve_tab.update_plot(data_dict['states'])
        self.force_viz_tab.update_data(data_dict['states'])
        if self.Plot_touch_ and read_touch and data_dict['touch']:
            self.image_tab.update_plot(data_dict['touch'])
        elapsed_time = time.time() - start_time
        if self.run_time:
            print(f"update_plot execution time: {elapsed_time:.6f} seconds")

    def reflash(self):
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(self.dt)  # Update every 100 ms