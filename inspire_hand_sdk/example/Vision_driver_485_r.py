# from inspire_dds import inspire_hand_touch,inspire_hand_ctrl,inspire_hand_state
# from inspire_dds import inspire_hand_touch,inspire_hand_ctrl,inspire_hand_state
import sys
from inspire_sdkpy import qt_tabs,inspire_sdk,inspire_hand_defaut
# import inspire_sdkpy
if __name__ == "__main__":
    app = qt_tabs.QApplication(sys.argv)

    ## 读取全部状态数据（含力度、电流、温度用于可视化）
    states_structure = [
            ('pos_act', 1534, 6, 'short'),
            ('angle_act', 1546, 6, 'short'),
            ('force_act', 1582, 6, 'short'),
            ('current', 1594, 6, 'short'),
            ('err', 1606, 6, 'byte'),
            ('status', 1612, 6, 'byte'),
            ('temperature', 1618, 6, 'byte')
        ]
    
    handler = inspire_sdk.ModbusDataHandler(LR='r', device_id=1, use_serial=True, serial_port='COM4',states_structure=states_structure)
    window = qt_tabs.MainWindow(data_handler=handler,dt=100,name="Right Hand Vision Driver",Plot_touch=True,run_time=False)
    window.reflash()
    window.show()
    sys.exit(app.exec_())