# SenseGlove Integration

This module connects the RH56DFTP right hand to a right-hand SenseGlove and provides three workflows:

- `test_robot_hand.py`: standalone robot-hand DDS test GUI
- `test_senseglove.py`: standalone SenseGlove haptics test GUI
- `haptic_bridge.py`: integrated tactile-to-haptics bridge GUI

## Layout

- `senseglove_client.py`: Python wrapper for `senseglove_bridge.exe`
- `haptic_bridge.py`: integrated bridge UI and mapping logic
- `test_robot_hand.py`: right-hand DDS monitor/control UI
- `test_senseglove.py`: SenseGlove haptic test UI

## Build the bridge

From the repository root:

```powershell
cd senseglove_bridge
.\build.bat
```

This builds:

- `senseglove_bridge.exe`
- `sgcore.dll`
- `sgconnect.dll`

The binary is not committed. Rebuild locally when needed.

## Run

### 1. Pure simulation

```powershell
.\senseglove_integration\start_haptic_bridge_sim.bat
```

### 2. Real robot + real SenseGlove

```powershell
.\senseglove_integration\start_haptic_bridge.bat
```

### 3. SenseGlove simulated, robot real

```powershell
.\senseglove_integration\start_haptic_bridge_senseglove_sim.bat
```

### 4. Standalone tests

```powershell
.\senseglove_integration\start_test_robot_hand.bat
.\senseglove_integration\start_test_senseglove_sim.bat
```

## Mapping

Robot hand force mapping:

- `force_act[0]` -> SenseGlove `Pinky`
- `force_act[1]` -> SenseGlove `Ring`
- `force_act[2]` -> SenseGlove `Middle`
- `force_act[3]` -> SenseGlove `Index`
- `force_act[4]` -> SenseGlove `Thumb`
- `force_act[5]` is not mapped to force feedback

Robot touch mapping:

- pinky touch -> `PinkyTip`
- ring touch -> `RingTip`
- middle touch -> `MiddleTip`
- index touch -> `IndexTip`
- thumb touch -> `ThumbTip`
- palm touch -> `WholeHand`

## Notes

- Current integration assumes right hand only.
- `SenseCom` must be installed and running for a real SenseGlove session.
- DDS startup requires the existing Inspire hand SDK environment to be installed in the workspace venv.
