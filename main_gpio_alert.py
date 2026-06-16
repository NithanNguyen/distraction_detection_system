"""
main_gpio_alert.py — Driver phần cứng cảnh báo cho main.py.
 
Sở hữu GPIO:
    GPIO17 (pin 11) — LED vàng
    GPIO27 (pin 13) — Active buzzer (HIGH = kêu)
 
API:
    update(alert_active: bool)  — gọi mỗi frame của vòng lặp chính
    cleanup()                    — gọi khi thoát (trong finally hoặc signal_handler)
 
Pattern theo yêu cầu:
    0 ≤ t < 2s sau khi alert xuất hiện:
        LED vàng nhấp nháy chu kỳ 0.5s (0.25s ON / 0.25s OFF), buzzer OFF.
    t ≥ 2s:
        LED vàng + buzzer đồng bộ, chu kỳ 1s (0.5s ON / 0.5s OFF).
    alert tắt:
        LED + buzzer tắt ngay lập tức, reset bộ đếm thời gian.
 
Backend: gpiozero + lgpio (chuẩn trên Raspberry Pi OS Bookworm/Trixie).
Nếu không init được GPIO (không phải Pi, thiếu thư viện, pin đã bị claim,...),
module sẽ in cảnh báo và chuyển sang no-op để không crash main.py.
"""
 
import time
 
# --- Khởi tạo backend lgpio và pin ---
_yellow = None
_buzz   = None
_ok     = False
 
try:
    from gpiozero import LED, Buzzer, Device
    from gpiozero.pins.lgpio import LGPIOFactory
 
    Device.pin_factory = LGPIOFactory()
 
    _YELLOW_PIN = 17
    _BUZZER_PIN = 27
 
    _yellow = LED(_YELLOW_PIN, initial_value=False)
    _buzz   = Buzzer(_BUZZER_PIN, initial_value=False)
    _ok     = True
    print(f"[GPIO_ALERT] OK — LED vang GPIO{_YELLOW_PIN}, Buzzer GPIO{_BUZZER_PIN}", flush=True)
except Exception as e:
    print(f"[GPIO_ALERT] Khong khoi tao duoc GPIO ({type(e).__name__}: {e}). "
          f"Bo qua cảnh bao phan cung, main.py van chay binh thuong.", flush=True)
 
 
# --- State ---
_alert_started_at = None  # type: ignore[var-annotated]
 
# Hằng số pattern (xem docstring)
_PHASE1_DURATION = 2.0   # 0..2s: cảnh báo nhẹ
_PHASE1_HALF     = 0.25  # toggle 0.25s → chu kỳ 0.5s
_PHASE2_HALF     = 0.5   # toggle 0.5s  → chu kỳ 1s
 
 
def update(alert_active: bool) -> None:
    """Cập nhật LED vàng + buzzer dựa trên trạng thái alert hiện tại.
    Gọi mỗi frame của main loop. An toàn để gọi với tần suất cao."""
    global _alert_started_at
    if not _ok:
        return
 
    if not alert_active:
        if _alert_started_at is not None:
            _alert_started_at = None
            _yellow.off()
            _buzz.off()
        return
 
    now = time.monotonic()
    if _alert_started_at is None:
        _alert_started_at = now
 
    elapsed = now - _alert_started_at
 
    if elapsed < _PHASE1_DURATION:
        # Phase 1 (0..2s): LED nháy 0.25/0.25, buzzer im
        on = (int(elapsed / _PHASE1_HALF) % 2) == 0
        _yellow.on() if on else _yellow.off()
        _buzz.off()
    else:
        # Phase 2 (>2s): LED + Buzzer đồng bộ, 0.5/0.5
        e2 = elapsed - _PHASE1_DURATION
        on = (int(e2 / _PHASE2_HALF) % 2) == 0
        if on:
            _yellow.on()
            _buzz.on()
        else:
            _yellow.off()
            _buzz.off()
 
 
def cleanup() -> None:
    """Tắt LED + buzzer và giải phóng pin. Gọi trong finally / signal handler."""
    if not _ok:
        return
    try:
        _yellow.off()
        _buzz.off()
        _yellow.close()
        _buzz.close()
        print("[GPIO_ALERT] Da don dep GPIO17 + GPIO27.", flush=True)
    except Exception as e:
        print(f"[GPIO_ALERT] Loi don dep: {e}", flush=True)
 
