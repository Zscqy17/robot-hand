

from types import SimpleNamespace
import threading
modbus_lock = threading.Lock()

# 数据定义   
data_sheet = [
    ("小拇指指端触觉数据", 3000, 18, (3, 3), "fingerone_tip_touch"),      # 小拇指指端触觉数据
    ("小拇指指尖触觉数据", 3018, 192, (12, 8), "fingerone_top_touch"),      # 小拇指指尖触觉数据
    ("小拇指指腹触觉数据", 3210, 160, (10, 8), "fingerone_palm_touch"),     # 小拇指指腹触觉数据
    ("无名指指端触觉数据", 3370, 18, (3, 3), "fingertwo_tip_touch"),      # 无名指指端触觉数据
    ("无名指指尖触觉数据", 3388, 192, (12, 8), "fingertwo_top_touch"),      # 无名指指尖触觉数据
    ("无名指指腹触觉数据", 3580, 160, (10, 8), "fingertwo_palm_touch"),     # 无名指指腹触觉数据
    ("中指指端触觉数据", 3740, 18, (3, 3), "fingerthree_tip_touch"),    # 中指指端触觉数据
    ("中指指尖触觉数据", 3758, 192, (12, 8), "fingerthree_top_touch"),    # 中指指尖触觉数据
    ("中指指腹触觉数据", 3950, 160, (10, 8), "fingerthree_palm_touch"),   # 中指指腹触觉数据
    ("食指指端触觉数据", 4110, 18, (3, 3), "fingerfour_tip_touch"),     # 食指指端触觉数据
    ("食指指尖触觉数据", 4128, 192, (12, 8), "fingerfour_top_touch"),     # 食指指尖触觉数据
    ("食指指腹触觉数据", 4320, 160, (10, 8), "fingerfour_palm_touch"),    # 食指指腹触觉数据
    ("大拇指指端触觉数据", 4480, 18, (3, 3), "fingerfive_tip_touch"),     # 大拇指指端触觉数据
    ("大拇指尖触觉数据", 4498, 192, (12, 8), "fingerfive_top_touch"),     # 大拇指尖触觉数据
    ("大拇指指中触觉数据", 4690, 18, (3, 3), "fingerfive_middle_touch"),  # 大拇指指中触觉数据
    ("大拇指指腹触觉数据", 4708, 192, (12, 8), "fingerfive_palm_touch"),    # 大拇指指腹触觉数据
    ("掌心触觉数据", 4900, 224, (14, 8), "palm_touch")                # 掌心触觉数据
]
status_codes = {
    0: "正在松开",
    1: "正在抓取",
    2: "位置到位停止",
    3: "力控到位停止",
    5: "电流保护停止",
    6: "电缸堵转停止",
    7: "电缸故障停止",
    255: "错误"
}
error_descriptions = {
    0: "堵转故障",
    1: "过温故障",
    2: "过流故障",
    3: "电机异常",
    4: "通讯故障"
}
def get_error_description(error_value):
    error_reasons = []
    # 检查每一位是否为1，如果为1则添加对应的故障说明
    for bit, description in error_descriptions.items():
        if error_value & (1 << bit):  # 使用位运算检查对应位是否为1
            error_reasons.append(description)
    return error_reasons

# 打印综合故障原因
def update_error_label(ERROR):
    error_summary = []
    for e in ERROR:
        binary_error = '{:04b}'.format(int(e))  # 转换为4位二进制表示
        error_reasons = get_error_description(int(e))  # 获取故障原因列表
        if error_reasons:
            error_summary.append(f"ERROR {e} ({binary_error}): " + ', '.join(error_reasons))
        else:
            error_summary.append(f"ERROR {e} ({binary_error}): 无故障")
    # 更新标签内容
    # print("\n".join(error_summary))
    return"\t".join(error_summary)
       
       
 
def get_inspire_hand_touch():
    return SimpleNamespace(
        fingerone_tip_touch=[0]*9,
        fingerone_top_touch=[0]*96,
        fingerone_palm_touch=[0]*80,
        fingertwo_tip_touch=[0]*9,
        fingertwo_top_touch=[0]*96,
        fingertwo_palm_touch=[0]*80,
        fingerthree_tip_touch=[0]*9,
        fingerthree_top_touch=[0]*96,
        fingerthree_palm_touch=[0]*80,
        fingerfour_tip_touch=[0]*9,
        fingerfour_top_touch=[0]*96,
        fingerfour_palm_touch=[0]*80,
        fingerfive_tip_touch=[0]*9,
        fingerfive_top_touch=[0]*96,
        fingerfive_middle_touch=[0]*9,
        fingerfive_palm_touch=[0]*96,
        palm_touch=[0]*112,
    )
    
def get_inspire_hand_state():
    return SimpleNamespace(
        pos_act=[0]*6,
        angle_act=[0]*6,
        force_act=[0]*6,
        current=[0]*6,
        err=[0]*6,
        status=[0]*6,
        temperature=[0]*6,
    ) 

defaut_ip='192.168.11.210'