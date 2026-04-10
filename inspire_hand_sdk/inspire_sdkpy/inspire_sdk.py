
from .inspire_hand_defaut import *

from pymodbus.client import ModbusTcpClient
from pymodbus.client import ModbusSerialClient

import numpy as np
import struct
import sys
import time
class ModbusDataHandler:
    def __init__(self, data=data_sheet, history_length=100, ip=None, port=6000, device_id=1, LR='r', use_serial=False, serial_port='/dev/ttyUSB0', baudrate=115200, states_structure=None, max_retries=5, retry_delay=2):
        """RS485/TCP Modbus 灵巧手通信
        Args:
            data (dict, optional): Tactile sensor register definition. Defaults to data_sheet.
            history_length (int, optional): Hand state history_length. Defaults to 100.
            ip (str, optional): ModbusTcp IP. Defaults to None will use 192.168.11.210.
            port (int, optional): ModbusTcp IP port. Defaults to 6000.
            device_id (int, optional): Hand ID. Defaults to 1.
            LR (str, optional): Left or right hand. Defaults to 'r'.
            use_serial (bool, optional): Whether to use serial mode. Defaults to False.
            serial_port (str, optional): Serial port name. Defaults to '/dev/ttyUSB0'.
            baudrate (int, optional): Serial baud rate. Defaults to 115200.
            states_structure (list, optional): List of tuples for state registers.
            max_retries (int, optional): Number of retries for connecting. Defaults to 5.
            retry_delay (int, optional): Delay between retries in seconds. Defaults to 2.
        """        
        self.data = data
        self.history_length = history_length
        self.history = {
            'POS_ACT': [np.zeros(history_length) for _ in range(6)],
            'ANGLE_ACT': [np.zeros(history_length) for _ in range(6)],
            'FORCE_ACT': [np.zeros(history_length) for _ in range(6)],
            'CURRENT': [np.zeros(history_length) for _ in range(6)],
            'ERROR': [np.zeros(history_length) for _ in range(6)],
            'STATUS': [np.zeros(history_length) for _ in range(6)],
            'TEMP': [np.zeros(history_length) for _ in range(6)]
        }
        self.use_serial = use_serial
        
        self.states_structure = states_structure or [
            ('pos_act', 1534, 6, 'short'),
            ('angle_act', 1546, 6, 'short'),
            ('force_act', 1582, 6, 'short'),
            ('current', 1594, 6, 'short'),
            ('err', 1606, 6, 'byte'),
            ('status', 1612, 6, 'byte'),
            ('temperature', 1618, 6, 'byte')
        ]
        if self.use_serial:
            self.client = ModbusSerialClient(port=serial_port, baudrate=baudrate, timeout=1)
            print("will use serial")
        else:
            if ip==None:
                self.client = ModbusTcpClient(defaut_ip, port=6000)
                print("will use defautl Tcp")
            else:
                self.client = ModbusTcpClient(ip, port=port)
                print("will use Tcp")

        # 尝试连接 Modbus 服务器，带重试机制
        self.connect_to_modbus(max_retries, retry_delay)
        self.device_id = device_id
        self.client.write_register(1004, 1, device_id=self.device_id)  # reset error       
            
    def connect_to_modbus(self, max_retries, retry_delay):
        """连接到 Modbus 服务器，并在失败时重试"""
        retries = 0
        while retries < max_retries:
            try:
                if not self.client.connect():
                    raise ConnectionError("Failed to connect to Modbus server.")
                print("Modbus client connected successfully.")
                return
            except ConnectionError as e:
                print(f"Connection attempt {retries + 1} failed: {e}")
                retries += 1
                if retries < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print("Max retries reached. Could not connect.")
                    raise   
    def set_angle(self, angles):
        """设置各自由度角度, angles: list of 6 int (0-1000, -1=不动)"""
        with modbus_lock:
            self.client.write_registers(1486, angles, device_id=self.device_id)

    def set_force(self, forces):
        """设置各自由度力控阈值, forces: list of 6 int (0-3000)"""
        with modbus_lock:
            self.client.write_registers(1498, forces, device_id=self.device_id)

    def set_speed(self, speeds):
        """设置各自由度速度, speeds: list of 6 int (0-1000)"""
        with modbus_lock:
            self.client.write_registers(1522, speeds, device_id=self.device_id)

    def set_pos(self, positions):
        """设置各自由度驱动器位置, positions: list of 6 int (0-2000)"""
        with modbus_lock:
            self.client.write_registers(1474, positions, device_id=self.device_id)

    def read(self, read_touch=False):
        matrixs = {}
        if read_touch:
            for i, (name, addr, length, size, var) in enumerate(self.data):
                value = self.read_and_parse_registers(addr, length // 2, 'short')
                if value is not None:
                    matrix = np.array(value).reshape(size)
                    matrixs[var] = matrix

        states = {}
        for attr_name, start_address, length, data_type in self.states_structure:
            states[attr_name] = self.read_and_parse_registers(start_address, length, data_type)

        STATE_KEY_MAP = {
            'pos_act': 'POS_ACT', 'angle_act': 'ANGLE_ACT',
            'force_act': 'FORCE_ACT', 'current': 'CURRENT',
            'err': 'ERROR', 'status': 'STATUS', 'temperature': 'TEMP',
        }
        return {
            'states': {STATE_KEY_MAP.get(k, k): v for k, v in states.items()},
            'touch': matrixs,
        }

    def read_and_parse_registers(self, start_address, num_registers, data_type='short'):
         with modbus_lock:
            # 读取寄存器
            response = self.client.read_holding_registers(start_address, count=num_registers, device_id=self.device_id)

            if not response.isError():
                if data_type == 'short':
                    # 将读取的寄存器打包为二进制数据
                    packed_data = struct.pack('>' + 'H' * num_registers, *response.registers)
                    # 将寄存器解包为带符号的 16 位整数 (short)
                    angles = struct.unpack('>' + 'h' * num_registers, packed_data)
                    return angles
                elif data_type == 'byte':
                    # 每个 Modbus 寄存器存储一个 byte 值
                    byte_list = []
                    for reg in response.registers:
                        byte_list.append(reg & 0xFF)
                    return byte_list
            else:
                print("Error reading registers")
                return None
            

if __name__ == "__main__":
    import qt_tabs 
    app = qt_tabs.QApplication(sys.argv)
    handler=ModbusDataHandler(data_sheet)
    window = qt_tabs.MainWindow(handler,data_sheet)
    window.reflash()
    window.show()
    sys.exit(app.exec_())
