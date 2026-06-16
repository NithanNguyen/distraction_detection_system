#!/usr/bin/env python3
"""
pi_controller.py — Boot watchdog cho dự án Drowsiness Detection.
 
Sở hữu GPIO:
    GPIO22 (pin 15) — LED xanh
    GPIO26 (pin 37) — Button (nối GND, internal pull-up, active-LOW)
 
Hành vi:
    IDLE   : LED xanh nháy 1Hz (chu kỳ 1s — toggle mỗi 0.5s).
             Bấm button → chuyển RUNNING.
    RUNNING: LED xanh sáng liên tục.
             Spawn main.py (subprocess, dùng Python venv).
             Bấm button → SIGTERM main.py, chờ tối đa 8s cho cleanup
                          (LED vàng/buzzer + camera), sau đó SIGKILL nếu cần.
                          → quay về IDLE.
             Nếu main.py tự exit (crash/người dùng đóng cửa sổ) → tự động về IDLE.
 
Chạy bằng Python 3.13 hệ thống (apt python3-gpiozero + python3-lgpio).
Khởi động qua systemd user service: pi-controller.service.
"""
 
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
 
from gpiozero import LED, Button, Device
from gpiozero.pins.lgpio import LGPIOFactory
 
# Ép backend lgpio (mặc định trên Trixie nhưng khai báo tường minh cho chắc)
Device.pin_factory = LGPIOFactory()
 
# =========================================================================
# CẤU HÌNH — sửa nếu đường dẫn project khác
# =========================================================================
PROJECT_DIR  = Path("/home/ce344/Documents/ce_comedians/project")
VENV_PYTHON  = PROJECT_DIR / "venv" / "bin" / "python3"
MAIN_SCRIPT  = PROJECT_DIR / "main.py"
 
GREEN_LED_PIN = 22
BUTTON_PIN    = 26
 
IDLE_HALF_PERIOD = 0.5   # 1Hz → toggle mỗi 0.5s (chu kỳ 1s)
SIGTERM_TIMEOUT  = 8.0   # giây — chờ main.py cleanup GPIO17/buzzer/camera
DEBOUNCE_WINDOW  = 1.5   # giây — chống bấm đúp ngoài ý muốn
LOOP_TICK        = 0.05  # 50ms — đủ độ phân giải cho blink
 
# =========================================================================
# Phần cứng
# =========================================================================
green_led = LED(GREEN_LED_PIN, initial_value=False)
button    = Button(BUTTON_PIN, pull_up=True, bounce_time=0.05)
 
# =========================================================================
# Trạng thái dùng chung (proc được truy cập từ main thread và callback thread)
# =========================================================================
_proc        = None           # type: subprocess.Popen | None
_lock        = threading.Lock()
_last_toggle = 0.0            # mốc thời gian lần toggle gần nhất
 
 
def _proc_alive_unlocked() -> bool:
    """Yêu cầu caller đã giữ _lock."""
    return _proc is not None and _proc.poll() is None
 
 
def _start_main_unlocked() -> None:
    """Yêu cầu caller đã giữ _lock và _proc đã None."""
    global _proc
    if not VENV_PYTHON.exists():
        print(f"[CONTROLLER] LOI: khong tim thay venv Python: {VENV_PYTHON}", flush=True)
        return
    if not MAIN_SCRIPT.exists():
        print(f"[CONTROLLER] LOI: khong tim thay main.py: {MAIN_SCRIPT}", flush=True)
        return
 
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":0")
    # XAUTHORITY thường đã có sẵn trong user session khi autologin graphical.
 
    print(f"[CONTROLLER] Khoi dong: {VENV_PYTHON} {MAIN_SCRIPT}", flush=True)
    _proc = subprocess.Popen(
        [str(VENV_PYTHON), str(MAIN_SCRIPT)],
        cwd=str(PROJECT_DIR),
        env=env,
    )
    print(f"[CONTROLLER] main.py PID={_proc.pid}", flush=True)
 
 
def _stop_main_unlocked() -> None:
    """Yêu cầu caller đã giữ _lock."""
    global _proc
    if not _proc_alive_unlocked():
        _proc = None
        return
 
    pid = _proc.pid
    print(f"[CONTROLLER] SIGTERM toi PID {pid}, cho cleanup ≤ {SIGTERM_TIMEOUT}s ...", flush=True)
    _proc.terminate()
    try:
        _proc.wait(timeout=SIGTERM_TIMEOUT)
        print(f"[CONTROLLER] main.py thoat sach (rc={_proc.returncode}).", flush=True)
    except subprocess.TimeoutExpired:
        print(f"[CONTROLLER] Qua {SIGTERM_TIMEOUT}s — SIGKILL.", flush=True)
        _proc.kill()
        _proc.wait()
        print("[CONTROLLER] main.py da bi force kill.", flush=True)
    _proc = None
 
 
def _reap_if_dead() -> None:
    """Gọi từ main loop. Nếu main.py tự thoát thì xóa reference."""
    global _proc
    with _lock:
        if _proc is not None and _proc.poll() is not None:
            rc = _proc.returncode
            _proc = None
            print(f"[CONTROLLER] main.py tu thoat (rc={rc}). Quay ve IDLE.", flush=True)
 
 
def _is_alive() -> bool:
    with _lock:
        return _proc_alive_unlocked()
 
 
def on_button_pressed() -> None:
    """Callback button — chạy ở thread riêng của gpiozero."""
    global _last_toggle
    now = time.monotonic()
    # Chống bấm đúp ngoài _lock để debug rõ
    if now - _last_toggle < DEBOUNCE_WINDOW:
        return
    with _lock:
        # Re-check trong lock
        if now - _last_toggle < DEBOUNCE_WINDOW:
            return
        _last_toggle = now
        if _proc_alive_unlocked():
            _stop_main_unlocked()
        else:
            _start_main_unlocked()
 
 
button.when_pressed = on_button_pressed
 
 
def main() -> int:
    print(f"[CONTROLLER] Khoi dong. LED xanh GPIO{GREEN_LED_PIN}, "
          f"button GPIO{BUTTON_PIN}. Project: {PROJECT_DIR}", flush=True)
    next_blink = time.monotonic()
    blink_high = False
    try:
        while True:
            now = time.monotonic()
            _reap_if_dead()
 
            if _is_alive():
                # RUNNING: LED solid
                if not green_led.is_lit:
                    green_led.on()
            else:
                # IDLE: blink 1Hz
                if now >= next_blink:
                    blink_high = not blink_high
                    if blink_high:
                        green_led.on()
                    else:
                        green_led.off()
                    next_blink = now + IDLE_HALF_PERIOD
 
            time.sleep(LOOP_TICK)
    except KeyboardInterrupt:
        print("\n[CONTROLLER] Nhan SIGINT.", flush=True)
    finally:
        print("[CONTROLLER] Don dep ...", flush=True)
        with _lock:
            _stop_main_unlocked()
        green_led.off()
        green_led.close()
        button.close()
    return 0
 
 
if __name__ == "__main__":
    sys.exit(main())
