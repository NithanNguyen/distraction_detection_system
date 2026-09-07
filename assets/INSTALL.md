# Installation Guide — Distraction Detection System

> Moved verbatim from the previous root `README.md` (sections 3–9). Kept as-is because the
> version pins and the failure modes behind them were established by trial on real hardware.
> Known-error catalogue: [`../INSTALL_GUIDE_PITFALLS.md`](../INSTALL_GUIDE_PITFALLS.md).

---

## 3. CHUẨN BỊ TRÊN MÁY x86 (Ubuntu/Windows) — Export ONNX

> Bước này thực hiện **một lần duy nhất** trên máy x86 có PyTorch, sau đó copy file sang Pi 4.

### Bước 3.1 — Tạo môi trường export tạm

```bash
python3 -m venv /tmp/yolo_export_env
source /tmp/yolo_export_env/bin/activate
pip install ultralytics
```

### Bước 3.2 — Export YOLO sang ONNX

```bash
python3 -c "
from ultralytics import YOLO
model = YOLO('yolo11n.pt')
model.export(format='onnx', imgsz=640, opset=12, simplify=True)
print('Export xong: yolo11n.onnx')
"
ls -lh yolo11n.onnx
# Mong đợi: ~10-11MB
```

> **Tại sao `opset=12`?** onnxruntime trên aarch64 hỗ trợ tốt nhất opset 11–13. `simplify=True` giảm số node, tăng tốc inference.

### Bước 3.3 — Copy file sang Pi 4

```bash
# Thay YOUR_PI_IP bằng IP thực (trên Pi 4 chạy: hostname -I)
scp ~/yolo11n.onnx phat@YOUR_PI_IP:~/Documents/ce_comedians/project/
```

Kiểm tra file đã tới trên Pi 4:

```bash
ls -lh ~/Documents/ce_comedians/project/yolo11n.onnx
# Mong đợi: 11M
```

---

## 4. CÀI ĐẶT TRÊN PI 4

### Bước 4.1 — Xóa setup cũ

```bash
rm -rf ~/Documents/ce_comedians/project/venv
ls ~/Documents/ce_comedians/project/
```

### Bước 4.2 — Xác nhận Python 3.11.9

```bash
cd ~/Documents/ce_comedians/project
pyenv local 3.11.9
python3 --version
# Phải ra: Python 3.11.9
```

> Nếu pyenv chưa có Python 3.11.9, cài trước:
> ```bash
> curl https://pyenv.run | bash
> source ~/.bashrc
> pyenv install 3.11.9
> ```

### Bước 4.3 — Tạo venv Python 3.11

```bash
python3 -m venv venv --system-site-packages
source venv/bin/activate
python3 --version   # Phải ra: Python 3.11.9
which python3       # Phải ra: .../project/venv/bin/python3
```

### Bước 4.4 — Cài numpy (pin version trước mọi thứ)

```bash
pip install --upgrade pip setuptools wheel
pip install "numpy>=1.26.4,<2"

python3 -c "import numpy as np; print('numpy:', np.__version__)"
# Phải ra: numpy: 1.26.4
```

### Bước 4.5 — Cài OpenCV

```bash
pip install "opencv-python==4.11.0.86"

python3 -c "import cv2; print('cv2:', cv2.__version__, '| file:', cv2.__file__)"
# Phải ra: cv2: 4.11.0 | file: .../venv/lib/.../cv2/__init__.py
```

Test imshow:

```bash
DISPLAY=:0 python3 -c "
import cv2, numpy as np
img = np.zeros((300,400,3), dtype=np.uint8)
cv2.putText(img, 'TEST OK', (50,150), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,0), 3)
cv2.imshow('Test', img)
cv2.waitKey(2000)
cv2.destroyAllWindows()
print('imshow OK!')
"
# Warning 'Qt platform plugin wayland' là bình thường — bỏ qua
```

> ⚠️ **Nếu bước này fail: dừng lại, không tiếp tục.** Đây là nền tảng của toàn bộ setup.

### Bước 4.6 — Cài Pillow (override PIL từ apt)

```bash
pip install Pillow --force-reinstall
```

### Bước 4.7 — Cài MediaPipe

```bash
pip install mediapipe \
    --find-links https://github.com/nickoala/mediapipe-on-raspberry-pi/releases/
# Phải thấy: mediapipe-0.10.18-cp311-cp311-...aarch64.whl

python3 -c "import mediapipe as mp; print('mediapipe:', mp.__version__)"
# Phải ra: mediapipe: 0.10.18
```

### Bước 4.8 — Cài ONNX Runtime

```bash
pip install onnxruntime

python3 -c "
import onnxruntime as ort
print('onnxruntime:', ort.__version__)
print('providers:', ort.get_available_providers())
"
# Mong đợi: onnxruntime: 1.26.0 | providers: [..., 'CPUExecutionProvider']
# Warning GPU (drm/card0, card1) là bình thường trên Pi 4 — bỏ qua
```

### Bước 4.9 — Kiểm tra numpy không bị kéo lên 2.x

```bash
python3 -c "import numpy as np; print('numpy:', np.__version__)"
# Nếu ra 2.x → chạy: pip install "numpy>=1.26.4,<2" --force-reinstall
```

---

## 6. KIỂM TRA TỔNG THỂ VÀ CHẠY

### Bước 6.1 — Kiểm tra toàn bộ môi trường

```bash
python3 -c "
import cv2, mediapipe as mp, numpy as np, onnxruntime as ort
print('cv2        :', cv2.__version__)
print('mediapipe  :', mp.__version__)
print('numpy      :', np.__version__)
print('onnxruntime:', ort.__version__)
assert tuple(int(x) for x in np.__version__.split('.')[:2]) < (2, 0), 'numpy >= 2!'
print('=== TAT CA OK ===')
"
```

### Bước 6.2 — Test ONNX inference độc lập

```bash
DISPLAY=:0 python3 -c "
import cv2, numpy as np, onnxruntime as ort

session = ort.InferenceSession('yolo11n.onnx', providers=['CPUExecutionProvider'])
cap = cv2.VideoCapture(0)
ok, frame = cap.read()
cap.release()

img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
img_r = cv2.resize(img, (640,640)).astype(np.float32)/255.0
img_r = np.expand_dims(np.transpose(img_r,(2,0,1)), 0)
inp = session.get_inputs()[0].name
out = session.run(None, {inp: img_r})
print('ONNX inference OK, output shape:', out[0].shape)
"
# Phải ra: ONNX inference OK, output shape: (1, 84, 8400)
```

### Bước 6.3 — Chạy project

```bash
export DISPLAY=:0
python3 main.py
```

---

## 7. BẢNG TỔNG HỢP: NÊN và KHÔNG NÊN

| | KHÔNG NÊN ❌ | NÊN ✅ |
|---|---|---|
| **Python version** | Python 3.13 (system default) | Python 3.11.9 (pyenv) |
| **OpenCV** | `apt python3-opencv` + `.pth` (cp313 không tương thích cp311) | `pip install opencv-python==4.11.0.86` |
| **OpenCV** | `opencv-python-headless` | `opencv-python==4.11.0.86` (có imshow) |
| **MediaPipe** | `pip install mediapipe` thẳng | `--find-links nickoala/releases` |
| **MediaPipe** | `mediapipe-rpi4` (binary 32-bit) | `mediapipe-0.10.18-cp311-aarch64` |
| **Pillow** | Để kế thừa từ apt | `pip install Pillow --force-reinstall` |
| **NumPy** | Để mặc định (bị kéo lên 2.x) | Pin: `numpy>=1.26.4,<2` ngay từ đầu |
| **YOLO inference** | `ultralytics` + `torch` (crash Pi 4) | `onnxruntime` + file `.onnx` |
| **Export ONNX** | Trên Pi 4 | Trên máy x86, copy `.onnx` sang Pi |

---

## 8. WARNINGS BÌNH THƯỜNG — KHÔNG CẦN XỬ LÝ

```
qt.qpa.plugin: Could not find the Qt platform plugin "wayland"
→ cv2 dùng Qt backend, imshow vẫn hoạt động qua X11/xcb

[W:onnxruntime] Failed to detect devices under "/sys/class/drm/card0"
→ onnxruntime tìm GPU không thấy, dùng CPU bình thường

Error in cpuinfo: prctl(PR_SVE_GET_VL) failed
INFO: Created TensorFlow Lite XNNPACK delegate for CPU.
W0000 inference_feedback_manager.cc: Feedback manager requires a model...
W0000 landmark_projection_calculator.cc: Using NORM_RECT without IMAGE_DIMENSIONS
→ Tất cả là warning nội bộ của mediapipe, bỏ qua
```

Fix permission warning (một lần duy nhất nếu cần):
```bash
chmod 700 /run/user/1000
```

---

## 9. KHỞI ĐỘNG LẠI PROJECT (LẦN SAU)

```bash
cd ~/Documents/ce_comedians/project
source venv/bin/activate
export DISPLAY=:0
python3 main.py
```
