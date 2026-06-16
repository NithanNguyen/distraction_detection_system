# RUN
```bash
cd ~/Documents/ce_comedians/project
/usr/bin/python3 pi_controller.py
```

# HƯỚNG DẪN CÀI ĐẶT PROJECT - 
> Raspberry Pi 4 · Debian GNU/Linux 13 (trixie) · ARM64 (aarch64) · Python 3.11.9 · Webcam USB
---

## 1. THÔNG TIN MÔI TRƯỜNG

| Thành phần | Thông tin |
|---|---|
| Hardware | Raspberry Pi 4 |
| OS | Debian GNU/Linux 13 (trixie) |
| Kernel | Linux 6.12.75+rpt-rpi-v8 |
| Architecture | ARM64 (aarch64) |
| Python | 3.11.9 (pyenv) — **bắt buộc**, không dùng 3.13 system |
| Camera | Webcam USB (`CAMERA_INDEX = 0`) |

### Dependencies cuối cùng

| Package | Version | Nguồn |
|---|---|---|
| Python | 3.11.9 | pyenv |
| cv2 (OpenCV) | 4.11.0 | pip (`opencv-python==4.11.0.86`) |
| mediapipe | 0.10.18 | pip (`--find-links nickoala/releases`) |
| numpy | 1.26.4 | pip (pinned `<2`) |
| onnxruntime | 1.26.0 | pip |
| ~~torch / ultralytics~~ | ~~—~~ | ❌ Không cài trên Pi 4 — crash `Illegal instruction` |

---

## 2. CÁC LỖI ĐÃ BIẾT VÀ CÁCH TRÁNH

### Lỗi 1 — Python 3.13 không có wheel MediaPipe
- **Triệu chứng:** `No matching distribution found for mediapipe`
- **Nguyên nhân:** Debian 13 mặc định Python 3.13; MediaPipe chưa có wheel cho `cp313-aarch64`.
- **Giải pháp:** Bắt buộc dùng **Python 3.11.9 qua pyenv**.

### Lỗi 2 — `mediapipe-rpi4` binary 32-bit sai architecture
- **Triệu chứng:** `No module named 'mediapipe.python._framework_bindings'`
- **Nguyên nhân:** `mediapipe-rpi4==0.8.8` được compile cho `cp37m-arm-linux-gnueabihf` (32-bit).
- **Giải pháp:** Dùng wheel từ community build của nickoala (cp311-aarch64).

### Lỗi 3 — `opencv-python` từ PyPI gây `Illegal instruction`
- **Triệu chứng:** `Illegal instruction` khi chạy cv2.
- **Nguyên nhân:** Bản pip compile với CPU instructions (AVX/SSE) không có trên Cortex-A72.
- **Giải pháp:** Dùng `opencv-python==4.11.0.86` từ pip (bản cp37-abi3 aarch64 tương thích).

### Lỗi 4 — cv2 apt (`cp313`) không load được trong venv Python 3.11
- **Triệu chứng:** `ModuleNotFoundError: No module named 'cv2'` dù đã tạo `.pth` file.
- **Nguyên nhân:** `python3-opencv` từ apt chỉ build cho cp313; Python 3.11 không load được binary này.
- **Giải pháp:** Cài `opencv-python==4.11.0.86` trực tiếp vào venv thay vì dùng `.pth`.

### Lỗi 5 — PIL conflict giữa apt và venv
- **Triệu chứng:** `ImportError: cannot import name '_imaging' from 'PIL'` khi import mediapipe.
- **Nguyên nhân:** matplotlib trong venv load PIL từ apt thay vì venv.
- **Giải pháp:** `pip install Pillow --force-reinstall` để override PIL trong venv.

### Lỗi 6 — NumPy conflict
- **Triệu chứng:** `mediapipe requires numpy<2` hoặc cv2 lỗi numpy khi import.
- **Nguyên nhân:** numpy 2.x từ apt hoặc bị kéo vào bởi dependency khác.
- **Giải pháp:** Pin numpy ngay từ đầu: `pip install "numpy>=1.26.4,<2"`.

### Lỗi 7 — PyTorch crash khi YOLO inference
- **Triệu chứng:** `Illegal instruction` ngay sau `model.predict()`.
- **Nguyên nhân:** `torch 2.x` compile với CPU instructions không có trên Cortex-A72; PyTorch chính thức không còn hỗ trợ Pi 4 từ torch 2.x.
- **Giải pháp:** Không cài PyTorch/ultralytics trên Pi 4. Dùng ONNX Runtime thay thế.

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

## 5. PATCH main.py ĐỂ DÙNG ONNX
(CÓ THỂ BỎ QUA NẾU CHƯA TẠO FILE .ommx)

Thay thế `ultralytics/YOLO` bằng `onnxruntime` trong `main.py`. Chạy 2 lệnh sau:

### Bước 5.1 — Đổi PHONE_MODEL_PATH

```bash
sed -i 's/PHONE_MODEL_PATH = "yolo11n.pt"/PHONE_MODEL_PATH = "yolo11n.onnx"/' main.py
grep "PHONE_MODEL_PATH" main.py
# Phải ra: PHONE_MODEL_PATH = "yolo11n.onnx"
```

### Bước 5.2 — Thay hàm load_phone_model và detect_phone

```bash
python3 - << 'EOF'
import re

with open("main.py", "r") as f:
    content = f.read()

new_load = '''def load_phone_model():
    if not USE_PHONE_DETECTION:
        return None, {}
    try:
        import onnxruntime as ort
        import ast
        session = ort.InferenceSession(
            PHONE_MODEL_PATH,
            providers=["CPUExecutionProvider"]
        )
        meta = session.get_modelmeta().custom_metadata_map
        names = {}
        if "names" in meta:
            names = ast.literal_eval(meta["names"])
        return session, names
    except Exception as e:
        print(f"[WARN] Khong tai duoc model phone: {e}")
        return None, {}'''

new_detect = '''def detect_phone(model, frame_bgr):
    detections = []
    if model is None:
        return detections
    try:
        PHONE_CLASS_ID = 67
        img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img, (640, 640))
        img_input = img_resized.astype(np.float32) / 255.0
        img_input = np.transpose(img_input, (2, 0, 1))
        img_input = np.expand_dims(img_input, axis=0)

        input_name = model.get_inputs()[0].name
        outputs = model.run(None, {input_name: img_input})

        predictions = outputs[0][0].T
        orig_h, orig_w = frame_bgr.shape[:2]
        scale_x = orig_w / 640.0
        scale_y = orig_h / 640.0

        for pred in predictions:
            cx, cy, w, h = pred[0], pred[1], pred[2], pred[3]
            class_scores = pred[4:]
            class_id = int(np.argmax(class_scores))
            conf = float(class_scores[class_id])
            if class_id != PHONE_CLASS_ID or conf < PHONE_CONF_THRESHOLD:
                continue
            x1 = max(0, int((cx - w / 2) * scale_x))
            y1 = max(0, int((cy - h / 2) * scale_y))
            x2 = min(orig_w - 1, int((cx + w / 2) * scale_x))
            y2 = min(orig_h - 1, int((cy + h / 2) * scale_y))
            detections.append({
                "box": (x1, y1, x2, y2),
                "conf": conf,
                "label": "cell phone",
            })
    except Exception as e:
        print(f"[WARN] Loi detect phone: {e}")
    return detections'''

content = re.sub(
    r'def load_phone_model\(\):.*?(?=\ndef )',
    new_load + '\n\n',
    content,
    flags=re.DOTALL
)
content = re.sub(
    r'def detect_phone\(model, frame_bgr\):.*?(?=\ndef )',
    new_detect + '\n\n',
    content,
    flags=re.DOTALL
)

with open("main.py", "w") as f:
    f.write(content)

print("Patch OK")
EOF
```

### Bước 5.3 — Xác nhận patch

```bash
grep -n "def load_phone_model\|def detect_phone\|YOLO\|onnxruntime\|PHONE_CLASS_ID" main.py
# Phải thấy onnxruntime và PHONE_CLASS_ID, KHÔNG thấy YOLO
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
