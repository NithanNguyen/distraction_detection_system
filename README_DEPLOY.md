# Hướng dẫn triển khai — Drowsiness Detection Controller

> **Mục tiêu:** biến project `main.py` thành sản phẩm đứng độc lập trên Pi 4:
> cắm điện → vào desktop → LED xanh tự nháy 1Hz; bấm button khởi động/tắt
> chương trình; có LED vàng + buzzer cảnh báo trực tiếp.
>
> **Môi trường đã kiểm chứng:** Raspberry Pi 4 Model B · Debian 13 (Trixie,
> kernel 6.12) · desktop Wayfire/labwc · Python 3.13 hệ thống · venv 3.11 cho
> project (đã có sẵn theo `INSTALL_GUIDE_PITFALLS.md`).

---

## 0. Trước khi bắt đầu — xác nhận username

Toàn bộ guide dưới đây có path tuyệt đối tới home directory. **Bạn cần biết
chính xác username của mình** để tránh sai một mạch xuyên suốt các file.

```bash
whoami           # → ghi nhớ output, ví dụ: ce344
echo "$HOME"     # → phải khớp /home/<username>
```

> Trong các đoạn bên dưới, mọi vị trí `<USER>` phải được thay bằng kết quả
> của `whoami` của chính bạn. File systemd unit dùng specifier `%h` để tự
> động lấy `$HOME` của user, nên **không có** `<USER>` hardcoded trong đó.
> Riêng `pi_controller.py` cần bạn đặt đúng `PROJECT_DIR` (mục 5.1).

---

## 1. Sơ đồ phần cứng

```
                       Raspberry Pi 4 (40-pin header)
                       ───────────────────────────────
   LED xanh ────[330Ω]──┤ GPIO22 (pin 15)
        anode           │
   cathode ──────────────┤ GND     (pin 14 hoặc 6, 9, 20...)

   LED vàng ────[330Ω]──┤ GPIO17 (pin 11)
        anode           │
   cathode ──────────────┤ GND     (dùng GND chung)

   Active buzzer (+) ────┤ GPIO27 (pin 13)
   Active buzzer (−) ────┤ GND
   (* Active buzzer kéo dòng < 25 mA — có thể nối thẳng. Nếu module
      của bạn ghi > 25 mA hoặc 5V thì PHẢI qua transistor + 5V.)

   Button: 2 chân  ──────┤ GPIO26 (pin 37)
                         │
                  ────────┤ GND     (pin 39, hoặc GND khác)
   (Không cần điện trở ngoài — code bật pull-up nội. Bấm = kéo xuống LOW.)
```

**Điện trở cho LED:** 220Ω–470Ω (330Ω là sweet spot cho LED 2V/20mA với
nguồn 3.3V Pi). Không bỏ điện trở — sẽ cháy LED và có thể hỏng GPIO.

**Pin layout tham chiếu:** `RP008341DS1raspberrypi4datasheet.pdf` mục GPIO
Pin Assignments.

---

## 2. Cấu trúc file

Sau khi triển khai, project của bạn sẽ có thêm 3 file:

```
~/Documents/ce_comedians/project/
├── main.py                  ← chỉnh sửa 3 vị trí (xem mục 4)
├── main_gpio_alert.py       ← MỚI — driver LED vàng + buzzer
├── pi_controller.py         ← MỚI — boot controller (LED xanh + button)
├── pi-controller.service    ← MỚI — systemd user unit
└── venv/                    ← venv 3.11 đã có
```

---

## 3. Cài đặt thư viện GPIO

### 3.1. Cho controller (Python 3.13 hệ thống)

Trên Raspberry Pi OS Trixie, `python3-gpiozero` và `python3-lgpio` thường
đã có sẵn, nhưng cứ chạy để chắc chắn:

```bash
sudo apt update
sudo apt install -y python3-gpiozero python3-lgpio
```

Kiểm tra (chạy bằng Python 3.13 hệ thống):

```bash
/usr/bin/python3 -c "from gpiozero import LED; from gpiozero.pins.lgpio import LGPIOFactory; print('OK')"
```

### 3.2. Cho main.py (venv 3.11)

Đây là phần **dễ vấp** vì lgpio chưa có wheel sẵn cho Python 3.11 trên ARM64,
phải compile từ source theo gói C `liblgpio-dev`.

```bash
# 1) Cài thư viện C system-wide
sudo apt install -y liblgpio-dev

# 2) Activate venv 3.11 và cài
cd ~/Documents/ce_comedians/project
source venv/bin/activate
pip install --upgrade pip
pip install gpiozero lgpio

# 3) Test trong venv (LƯU Ý: dùng `python3`, KHÔNG dùng `/usr/bin/python3`
#    vì /usr/bin/python3 sẽ trỏ vào Python 3.13 hệ thống, bypass venv)
python3 -c "from gpiozero import LED, Buzzer; from gpiozero.pins.lgpio import LGPIOFactory; print('venv GPIO OK')"
```

**Nếu `pip install lgpio` báo lỗi `cannot find -llgpio`:** chứng tỏ
`liblgpio-dev` chưa cài hoặc thiếu. Cài lại bước 1, hoặc compile thủ công
theo `https://abyz.me.uk/lg/download.html`.

---

## 4. Sửa `main.py` — (Đã sửa thì SKIP bước này)

Mở `main.py` và thêm chính xác 3 đoạn sau. **KHÔNG xóa/sửa gì khác.**

### 4.1. Thêm import (ngay sau dòng `import socket` — khoảng dòng 21)

```python
import socket
import main_gpio_alert   # ← THÊM DÒNG NÀY
```

### 4.2. Drive LED + buzzer mỗi frame

Tìm đoạn này (khoảng dòng 1003–1007, sau khối `low_light_active`):

```python
            low_light_active = low_light_since is not None and (now - low_light_since) >= LOW_LIGHT_SECONDS
            if low_light_active:
                alert_messages.clear()
                status = "Anh sang yeu - khong the giam sat"
                status_color = (0, 165, 255)
```

Thêm **ngay sau** khối if đó:

```python
            # ===== DRIVE HARDWARE ALERT (LED vàng + buzzer) =====
            main_gpio_alert.update(len(alert_messages) > 0)
```

Logic: bất kỳ alert nào (`alert_messages` không rỗng) → bật pattern.
Khi ánh sáng yếu, `alert_messages.clear()` ở trên đã reset → LED/buzzer
sẽ tắt.

### 4.3. Cleanup khi thoát

Tìm khối `finally:` ở cuối file (khoảng dòng 1084–1099):

```python
    finally:
        print("\n[INFO] Giai phong camera va cua so hien thi...")
        if cap is not None:
            try:
                cap.release()
            except Exception as e:
                print(f"[ERROR] Loi giai phong camera: {e}")
        cv2.destroyAllWindows()
```

Thêm **ngay sau** `cv2.destroyAllWindows()`:

```python
        cv2.destroyAllWindows()
        main_gpio_alert.cleanup()   # ← THÊM DÒNG NÀY
```

**Tại sao đặt sau `destroyAllWindows`?** Khi nhận SIGTERM, `signal_handler`
raise `KeyboardInterrupt` → rơi vào `finally` → camera release → cửa sổ
đóng → LED/buzzer tắt → GPIO giải phóng. Tuần tự rõ ràng, dễ debug.

---

## 5. Đặt 3 file mới vào project

### 5.1. Sửa `PROJECT_DIR` trong `pi_controller.py` cho khớp username

Mở `pi_controller.py`, tìm dòng `PROJECT_DIR` (khoảng dòng 39) và sửa cho
đúng username của bạn (output của `whoami` từ Mục 0):

```python
PROJECT_DIR  = Path("/home/<USER>/Documents/ce_comedians/project")
```

> **Pitfall đã thực sự gặp phải:** Nếu `pi_controller.py` ghi user khác
> với user đang dùng (ví dụ giữ `phat` từ template trong khi user thật là
> `ce344`), controller vẫn start được và LED vẫn nháy, **nhưng** khi bấm
> button sẽ log lỗi `LOI: khong tim thay venv Python` và không spawn
> được main.py. Lỗi này im lặng cho đến lúc bấm.

### 5.2. Cấp quyền thực thi và test driver alert

```bash
cd ~/Documents/ce_comedians/project
chmod +x pi_controller.py

# Test main_gpio_alert độc lập (KHÔNG cần camera)
source venv/bin/activate
python3 -c "
import main_gpio_alert, time
print('Bat alert 4s...')
for _ in range(80):    # 80 * 0.05 = 4s
    main_gpio_alert.update(True)
    time.sleep(0.05)
print('Tat alert 1s...')
for _ in range(20):
    main_gpio_alert.update(False)
    time.sleep(0.05)
main_gpio_alert.cleanup()
"
```

**Kết quả mong đợi:**
- 0–2s: LED vàng nhấp nháy nhanh (chu kỳ 0.5s), buzzer im.
- 2–4s: LED vàng + buzzer cùng nháy chậm hơn (chu kỳ 1s).
- Sau đó: tắt hoàn toàn.

Nếu LED vàng không sáng → kiểm tra chiều LED (anode/cathode), điện trở,
GND chung.

Nếu buzzer chỉ "tick" mà không kêu liên tục → nó là **passive buzzer**,
không phải active (lúc đó cần đổi sang `Buzzer.beep()` với PWM).

---

## 6. Test controller thủ công (trước khi đăng ký systemd)

```bash
deactivate   # rời venv 3.11
cd ~/Documents/ce_comedians/project
/usr/bin/python3 pi_controller.py
```

**Quan sát:**
1. LED xanh bắt đầu nháy mỗi 1s.
2. Bấm button → cửa sổ camera mở (qua `main.py`), LED xanh sáng liên tục.
3. Bấm button lần 2 → trong vòng ≤ 8s, cửa sổ camera đóng, LED vàng +
   buzzer tắt sạch, LED xanh quay về nháy 1Hz.
4. Lặp lại tùy ý.

Dừng controller: `Ctrl+C` — controller sẽ tự gửi SIGTERM cho main.py
rồi tắt LED.

**Nếu bấm button không phản ứng:** test isolated:
```bash
/usr/bin/python3 -c "
from gpiozero import Button
b = Button(26, pull_up=True)
b.wait_for_press()
print('Da bam!')
"
```

---

## 7. Đăng ký systemd user service — chạy tự động khi boot

### 7.1. ⚠️ Vì sao KHÔNG dùng `graphical-session.target` (pitfall thực tế)

Hướng dẫn cũ trên mạng (và phiên bản đầu tiên của file này) thường gắn unit
vào `graphical-session.target`:

```ini
After=graphical-session.target
PartOf=graphical-session.target
[Install]
WantedBy=graphical-session.target
```

**Vấn đề:** Theo `systemd.special(7)`, `graphical-session.target` chỉ được
activate khi **session manager của desktop chủ động gọi nó**. Trên Pi OS
Trixie với Wayfire/labwc, target này **không bao giờ active** trong thực tế
— có thể kiểm chứng:

```bash
systemctl --user list-units --type=target --all | grep graphical
# → graphical-session.target  loaded  inactive dead
```

Hậu quả: `WantedBy=graphical-session.target` → systemd không có lý do start
service → LED không nháy, không có cả log lỗi (vì chưa từng thử start).

**Giải pháp đã được kiểm chứng:** dùng `default.target` (luôn lên khi user
systemd khởi động sau autologin). LED xanh nháy là việc thuần GPIO — không
cần DISPLAY; khi user bấm button và spawn `main.py`, desktop đã lên rồi
nên `cv2.imshow` có DISPLAY=:0 bình thường.

### 7.2. Nội dung file `pi-controller.service` (chuẩn)

```ini
[Unit]
Description=Drowsiness Detection — Boot Controller (green LED + button)
# Cho desktop dung gan xong neu co the, nhung khong phu thuoc bat buoc
After=graphical-session.target default.target
Wants=graphical-session.target

[Service]
Type=simple
# %h = $HOME cua user dang chay service → khong can hardcode username
ExecStart=/usr/bin/python3 %h/Documents/ce_comedians/project/pi_controller.py
Restart=on-failure
RestartSec=3
TimeoutStopSec=15
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

Hai đặc điểm cốt lõi:

| Trường | Lý do |
|---|---|
| `WantedBy=default.target` | `default.target` của **user systemd** trỏ về `basic.target` và luôn active sau khi user systemd khởi động (qua autologin hoặc lingering). Không phụ thuộc DE. |
| `Wants=graphical-session.target` (chứ KHÔNG `Requires/PartOf`) | Mềm — nếu DE có activate được thì chờ, nếu không thì vẫn start. Không bị "tắt theo" target cha. |
| `%h` specifier | Tự lấy `$HOME` đúng user → tránh hardcode `phat`/`ce344`. Specifier hợp lệ trong user unit (xem `systemd.unit(7)` mục Specifiers). |

### 7.3. Cài đặt và enable

```bash
# 1) Copy unit vao thu muc user systemd
mkdir -p ~/.config/systemd/user
cp ~/Documents/ce_comedians/project/pi-controller.service \
   ~/.config/systemd/user/pi-controller.service

# 2) Reload + enable + start
systemctl --user daemon-reload
systemctl --user enable  pi-controller.service
systemctl --user start   pi-controller.service

# 3) Kiem tra — phai thay "Active: active (running)"
systemctl --user status pi-controller.service
```

LED xanh **phải nháy 1Hz ngay tại bước 3 này**, chưa cần reboot.

Nếu service `Active: failed` → đọc log:
```bash
journalctl --user -u pi-controller.service -b --no-pager
```

### 7.4. Bật lingering (bảo hiểm)

```bash
sudo loginctl enable-linger $(whoami)
```

Cho phép user systemd instance lên ngay cả khi autologin có trục trặc nhẹ
về thời điểm. Với autologin đang OK thì lệnh này dư, nhưng vô hại và làm
hệ thống resilient hơn. Tham chiếu: `loginctl(1)` mục `enable-linger`.

### 7.5. Test reboot

```bash
sudo reboot
```

Khi Pi vào desktop, LED xanh phải bắt đầu nháy 1Hz trong vòng vài giây.

### 7.6. Tại sao USER service mà không phải SYSTEM service

| | User service | System service |
|---|---|---|
| `DISPLAY=:0` cho `cv2.imshow` | ✓ tự động (inherit từ session) | Phải set `Environment=DISPLAY=:0` + `XAUTHORITY=...` |
| Quyền GPIO | ✓ user đã ở group `gpio` | ✓ root, hoặc user nếu set `User=` |
| Dừng khi user logout | ✓ (đúng hành vi mong muốn) | ✗ tiếp tục chạy |
| Debug | `journalctl --user -u ...` | `sudo journalctl -u ...` |

Với autologin graphical, user service là lựa chọn sạch hơn rất nhiều.

---

## 8. Pattern cảnh báo — minh họa thời gian

```
Trạng thái alert:    OFF │ ON ────────────────────────────────────── │ OFF
Thời gian (s):       ────┼─0────0.5───1───1.5───2────2.5───3────3.5──┼────
                         │                                            │
LED vàng:           OFF │ ░▓░▓░▓░▓░▓░▓░▓░▓░▓░▓░▓░▓ │ ▓▓▓▓▓░░░░░▓▓▓▓▓░░░░░ │ OFF
                         │ ──── Phase 1 (0–2s) ──── │ ── Phase 2 (>2s) ── │
                         │ 0.25 on / 0.25 off       │ 0.5 on / 0.5 off     │
                         │ buzzer IM                │ buzzer KÊU đồng bộ   │
Buzzer:              OFF │ ──────────────────────── │ ▓▓▓▓▓░░░░░▓▓▓▓▓░░░░░ │ OFF
```

Khi `alert_messages` đột ngột rỗng (ví dụ người dùng tỉnh lại, mặt trở
lại bình thường): LED vàng + buzzer tắt **ngay frame kế tiếp**, đồng hồ
phase reset về 0.

---

## 9. Gỡ rối phổ biến

### 9.1. Quy trình chẩn đoán chuẩn (chạy 4 lệnh này trước khi đoán)

```bash
# 1. Username thuc te
whoami

# 2. Service co active khong?
systemctl --user status pi-controller.service

# 3. Log day du tu lan boot nay
journalctl --user -u pi-controller.service -b --no-pager

# 4. graphical-session.target co duoc activate khong?
systemctl --user list-units --type=target --all | grep graphical
```

### 9.2. Bảng triệu chứng → nguyên nhân

| Triệu chứng | Nguyên nhân khả năng cao | Cách xử lý |
|---|---|---|
| `Active: inactive (dead)` + journal `No entries` + `graphical-session.target inactive dead` | Unit đang gắn `WantedBy=graphical-session.target` nhưng target không bao giờ lên trên Wayfire/labwc | Đổi sang `WantedBy=default.target` theo Mục 7.2 |
| `Active: failed` + journal `status=203/EXEC` hoặc "No such file" | Path trong `ExecStart` sai (sai username, sai thư mục) | Dùng `%h/Documents/...` thay vì hardcode `/home/<user>/...` |
| LED xanh nháy bình thường nhưng bấm button log `LOI: khong tim thay venv Python` | `PROJECT_DIR` trong `pi_controller.py` sai username (ví dụ `phat` trong khi user thật là `ce344`) | Sửa dòng `PROJECT_DIR = Path(...)` cho khớp `whoami` |
| `main.py` mở nhưng không thấy cửa sổ camera | `DISPLAY` chưa set | Trong unit thêm `Environment=DISPLAY=:0` (thường không cần với user service) |
| LED vàng/buzzer không phản ứng khi có alert | Module `main_gpio_alert` import lỗi trong venv | Trong log main.py có `[GPIO_ALERT] Khong khoi tao duoc...` → cài lại `lgpio` trong venv (Mục 3.2) |
| Bấm button không tắt được main.py (treo > 8s) | `cap.release()` block, controller phải SIGKILL | Tăng `SIGTERM_TIMEOUT` trong `pi_controller.py` hoặc debug `main.py` |
| GPIO bị giữ sau crash | Process trước chưa release | Reboot, hoặc `sudo lgpio-info` |
| Bấm button hoàn toàn không gì xảy ra (kể cả khi chạy manual) | Sai pin, button hỏng, hoặc pull-up không hoạt động | Test isolated bằng snippet `Button(26, pull_up=True).wait_for_press()` |

---

## 10. Tham chiếu

- Raspberry Pi (12/2025) — Trixie release notes:
  https://www.raspberrypi.com/news/trixie-the-new-version-of-raspberry-pi-os/
  Xác nhận Python 3.13 default, `python3-lgpio` cài system-wide.
- gpiozero documentation: https://gpiozero.readthedocs.io/
- gpiozero pin factories (lgpio):
  https://gpiozero.readthedocs.io/en/latest/api_pins.html
- lgpio C library: https://abyz.me.uk/lg/lgpio.html
- systemd special targets (`graphical-session.target` activation rules):
  https://www.freedesktop.org/software/systemd/man/systemd.special.html
- systemd unit file specifiers (`%h`, `%u`, ...):
  https://www.freedesktop.org/software/systemd/man/systemd.unit.html#Specifiers
- `loginctl enable-linger`:
  https://www.freedesktop.org/software/systemd/man/loginctl.html
- Pi 4 GPIO map: `RP008341DS1raspberrypi4datasheet.pdf` (file đính kèm
  project), mục GPIO Pin Assignments.

---

## Phụ lục A — Lịch sử các pitfall đã thực sự gặp và sửa

Phần này ghi lại các lỗi đã gặp trong quá trình triển khai để các lần
deploy sau không lặp lại.

### A.1. Sai username giữa `pi_controller.py` và `pi-controller.service`

- **Triệu chứng:** Mỗi file hardcode một username khác nhau (template để
  `phat`, user thật là `ce344`).
- **Hệ quả:** Tùy hướng sai mà service không start được, hoặc service
  start được nhưng button không spawn được main.py.
- **Khắc phục đã áp dụng:**
  - `pi-controller.service` → dùng specifier `%h` thay vì hardcode path.
  - `pi_controller.py` → sửa `PROJECT_DIR` cho khớp `whoami`.

### A.2. `WantedBy=graphical-session.target` không kích hoạt trên Wayfire

- **Triệu chứng:** Sau reboot, `systemctl --user status pi-controller`
  cho `Active: inactive (dead)`, journal hoàn toàn rỗng (`No entries`),
  trong khi `enable` đã thành công.
- **Nguyên nhân đã xác minh:**
  `systemctl --user list-units --type=target --all | grep graphical`
  cho `graphical-session.target  inactive dead`. Wayfire/labwc trên Pi
  OS Trixie không activate target này, nên không có trigger để start
  service.
- **Khắc phục đã áp dụng:** Đổi `WantedBy=graphical-session.target` →
  `WantedBy=default.target`, đồng thời hạ ràng buộc từ
  `PartOf=graphical-session.target` xuống `Wants=graphical-session.target`
  (mềm). Sau đó:
  ```bash
  systemctl --user disable pi-controller.service
  systemctl --user daemon-reload
  systemctl --user enable  pi-controller.service
  systemctl --user start   pi-controller.service
  ```
  LED xanh nháy ngay lập tức, reboot xong vẫn nháy.
