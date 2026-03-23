"""
SenseGlove Python Client - communicates with senseglove_bridge.exe via subprocess.

Usage:
    from senseglove_client import SenseGloveClient
    
    client = SenseGloveClient()
    client.start()
    client.init()
    status = client.get_status()
    client.set_force_feedback([0.5, 0.0, 0.0, 0.0, 0.0])  # thumb 50%
    client.send_waveform(1.0, 0.2, 80.0, EHapticLocation.WholeHand)
    client.stop_haptics()
    client.close()
"""

import subprocess
import json
import os
import threading
import time
from enum import IntEnum
from typing import Optional
from pathlib import Path


class EHapticLocation(IntEnum):
    """SenseGlove haptic motor locations"""
    Unknown = 0
    ThumbTip = 1
    IndexTip = 2
    MiddleTip = 3
    RingTip = 4
    PinkyTip = 5
    PalmIndexSide = 6
    PalmPinkySide = 7
    WholeHand = 8


class SenseGloveFinger(IntEnum):
    """SenseGlove finger indices for force feedback"""
    Thumb = 0
    Index = 1
    Middle = 2
    Ring = 3
    Pinky = 4


class SenseGloveClient:
    """Python client for the SenseGlove C++ bridge process."""
    
    def __init__(self, bridge_path: Optional[str] = None):
        """
        Args:
            bridge_path: Path to senseglove_bridge.exe. If None, auto-detects.
        """
        if bridge_path is None:
            # Auto-detect: look in senseglove_bridge/bin/ relative to this file
            base = Path(__file__).parent.parent / "senseglove_bridge" / "bin"
            bridge_path = str(base / "senseglove_bridge.exe")
        
        self.bridge_path = bridge_path
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._running = False
        
    def start(self) -> dict:
        """Start the bridge process. Returns the ready message."""
        if not os.path.exists(self.bridge_path):
            raise FileNotFoundError(
                f"Bridge executable not found: {self.bridge_path}\n"
                f"Please run senseglove_bridge/build.bat first."
            )
        
        bridge_dir = os.path.dirname(self.bridge_path)
        
        self.process = subprocess.Popen(
            [self.bridge_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=bridge_dir,
            text=True,
            bufsize=1,  # Line buffered
        )
        self._running = True
        
        # Read ready message
        response = self._read_response()
        if not response or not response.get("ok"):
            raise RuntimeError(f"Bridge failed to start: {response}")
        return response
    
    def _send_command(self, cmd: str) -> dict:
        """Send a command and read the response."""
        if not self._running or self.process is None:
            raise RuntimeError("Bridge not running")
        
        with self._lock:
            try:
                self.process.stdin.write(cmd + "\n")
                self.process.stdin.flush()
                return self._read_response()
            except (BrokenPipeError, OSError) as e:
                self._running = False
                raise RuntimeError(f"Bridge communication error: {e}")
    
    def _read_response(self) -> dict:
        """Read one JSON line from stdout."""
        if self.process is None:
            return {"ok": False, "error": "Process not started"}
        
        line = self.process.stdout.readline()
        if not line:
            self._running = False
            return {"ok": False, "error": "Bridge process ended unexpectedly"}
        
        try:
            return json.loads(line.strip())
        except json.JSONDecodeError:
            return {"ok": False, "error": f"Invalid JSON: {line.strip()}"}
    
    def init(self) -> dict:
        """Initialize SenseGlove library and try to start SenseCom."""
        return self._send_command("INIT")
    
    def get_status(self) -> dict:
        """Get device connection status."""
        return self._send_command("STATUS")
    
    def set_force_feedback(self, levels: list[float]) -> dict:
        """
        Set force feedback levels for all 5 fingers.
        
        Args:
            levels: List of 5 floats (0.0-1.0) for [Thumb, Index, Middle, Ring, Pinky]
        """
        if len(levels) != 5:
            raise ValueError("Must provide exactly 5 force feedback levels")
        clamped = [max(0.0, min(1.0, v)) for v in levels]
        cmd = "FFB " + " ".join(f"{v:.4f}" for v in clamped)
        return self._send_command(cmd)
    
    def set_vibration(self, location: EHapticLocation, level: float) -> dict:
        """
        Set vibration level at a specific location.
        
        Args:
            location: EHapticLocation value
            level: 0.0-1.0
        """
        level = max(0.0, min(1.0, level))
        return self._send_command(f"VIBRO {int(location)} {level:.4f}")
    
    def send_waveform(self, amplitude: float, duration: float, 
                      frequency: float, location: EHapticLocation) -> dict:
        """
        Send a custom vibration waveform.
        
        Args:
            amplitude: 0.0-1.0
            duration: seconds
            frequency: Hz
            location: EHapticLocation value
        """
        amplitude = max(0.0, min(1.0, amplitude))
        return self._send_command(
            f"WAVEFORM {amplitude:.4f} {duration:.4f} {frequency:.1f} {int(location)}"
        )
    
    def set_wrist_squeeze(self, level: float) -> dict:
        """
        Set wrist squeeze level (Nova 2.0 only).
        
        Args:
            level: 0.0-1.0
        """
        level = max(0.0, min(1.0, level))
        return self._send_command(f"SQUEEZE {level:.4f}")
    
    def stop_haptics(self) -> dict:
        """Stop all haptics."""
        return self._send_command("STOP")
    
    def close(self):
        """Shut down the bridge process."""
        if self._running and self.process:
            try:
                self._send_command("QUIT")
            except Exception:
                pass
            
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                if self.process:
                    self.process.kill()
            
            self._running = False
            self.process = None
    
    @property
    def is_running(self) -> bool:
        return self._running and self.process is not None and self.process.poll() is None
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def __del__(self):
        self.close()


class SenseGloveSimulator:
    """
    Simulated SenseGlove client for testing without hardware.
    Implements the same interface as SenseGloveClient.
    """
    
    def __init__(self):
        self._running = False
        self._ffb_levels = [0.0] * 5
        self._vibro_levels = {}
        self._squeeze_level = 0.0
        self._connected = True  # simulated
    
    def start(self) -> dict:
        self._running = True
        return {"ok": True, "ready": True, "simulated": True}
    
    def init(self) -> dict:
        return {"ok": True, "version": "Simulated v1.0", "sensecom": True}
    
    def get_status(self) -> dict:
        return {
            "ok": True,
            "right_connected": self._connected,
            "left_connected": False,
            "gloves": 1 if self._connected else 0,
            "type": "Simulated Nova2Glove",
            "supports_waveform": True,
            "supports_wrist_squeeze": True,
        }
    
    def set_force_feedback(self, levels: list[float]) -> dict:
        self._ffb_levels = [max(0.0, min(1.0, v)) for v in levels]
        return {"ok": True}
    
    def set_vibration(self, location: EHapticLocation, level: float) -> dict:
        self._vibro_levels[location] = max(0.0, min(1.0, level))
        return {"ok": True}
    
    def send_waveform(self, amplitude: float, duration: float,
                      frequency: float, location: EHapticLocation) -> dict:
        return {"ok": True}
    
    def set_wrist_squeeze(self, level: float) -> dict:
        self._squeeze_level = max(0.0, min(1.0, level))
        return {"ok": True}
    
    def stop_haptics(self) -> dict:
        self._ffb_levels = [0.0] * 5
        self._vibro_levels.clear()
        self._squeeze_level = 0.0
        return {"ok": True}
    
    def close(self):
        self._running = False
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.close()
