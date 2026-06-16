# HƯỚNG DẪN CÀI ĐẶT TRÁNH LỖI — Drowsiness Detection Project
> Raspberry Pi 4 · Debian GNU/Linux 13 (trixie) · ARM64 (aarch64) · Python · Webcam USB

---

## ⚠️ TÓM TẮT CÁC LỖI ĐÃ GẶP VÀ CÁCH TRÁNH

---

### LỖI 1 — Python 3.13 không có wheel MediaPipe

**Triệu chứng:**
```
ERROR: Could not find a version that satisfies the requirement mediapipe (from versions: none)
ERROR: No matching distribution found for mediapipe
```

**Nguyên nhân:** Debian 13 (trixie) mặc định dùng Python 3.13. MediaPipe chưa có wheel cho `cp313-aarch64` trên PyPI hay piwheels. Không có phiên bản nào của mediapipe (kể cả 0.10.9, 0.10.11, 0.10.14, 0.10.18) hoạt động với Python 3.13.

**Cách tránh:** **Bắt buộc dùng Python 3.11** (cài qua pyenv). KHÔNG dùng Python 3.13 mặc định của hệ thống.

```bash
# Cài pyenv và Python 3.11 TRƯỚC KHI làm bất cứ điều gì khác
curl https://pyenv.run | bash
source ~/.bashrc
pyenv install 3.11.9
cd ~/Documents/ce_comedians/project
pyenv local 3.11.9
python3 --version  # Phải ra: Python 3.11.9
```

---

### LỖI 2 — `mediapipe-rpi4` binary compile cho Python 3.7 32-bit

**Triệu chứng:**
```
ModuleNotFoundError: No module named 'mediapipe.python._framework_bindings'
```
```bash
find venv -name "*.so"
# Ra: _framework_bindings.cpython-37m-arm-linux-gnueabihf.so  ← 32-bit, sai!
```

**Nguyên nhân:** `mediapipe-rpi4==0.8.8` được compile cho `cp37m-arm-linux-gnueabihf` (Python 3.7, 32-bit ARM), không tương thích với Pi 4 ARM64 (aarch64).

**Cách tránh:** KHÔNG dùng `mediapipe-rpi4`. Dùng wheel từ community build:
```bash
pip install mediapipe \
    --find-links https://github.com/nickoala/mediapipe-on-raspberry-pi/releases/
# Sẽ cài mediapipe-0.10.18-cp311-cp311-linux_aarch64 — đúng binary
```

---

### LỖI 3 — opencv-python từ PyPI gây `Illegal instruction` trên Pi 4

**Triệu chứng:**
```
Illegal instruction
qt.qpa.plugin: Could not find the Qt platform plugin "wayland"
```

**Nguyên nhân:** `opencv-python` từ PyPI được compile với CPU instructions (AVX/SSE) không có trên ARM Cortex-A72 của Pi 4. Bản này cũng dùng Qt thay vì GTK.

**Cách tránh:** KHÔNG cài `opencv-python`, `opencv-contrib-python` từ pip. Dùng **cv2 từ apt** (được compile đúng cho Pi 4):
```bash
sudo apt install -y python3-opencv
# cv2 sẽ ở: /usr/lib/python3/dist-packages/cv2.cpython-313-aarch64-linux-gnu.so
```

Sau đó link vào venv Python 3.11 bằng `.pth` file:
```bash
echo "/usr/lib/python3/dist-packages" > \
    venv/lib/python3.11/site-packages/system_cv2.pth
```

---

### LỖI 4 — `opencv-python-headless` không có `cv2.imshow()`

**Triệu chứng:**
```
cv2.error: The function is not implemented. Rebuild the library with Windows,
GTK+ 2.x or Cocoa support.
```

**Nguyên nhân:** Bản `headless` không có GUI support — không thể dùng `cv2.imshow()`.

**Cách tránh:** KHÔNG cài `opencv-python-headless` hay `opencv-contrib-python-headless`. Chỉ dùng cv2 từ apt như hướng dẫn ở Lỗi 3.

---

### LỖI 5 — Xung đột numpy giữa mediapipe và ultralytics

**Triệu chứng:**
```
mediapipe 0.10.18 requires numpy<2, but you have numpy 2.4.4 which is incompatible.
opencv-python 4.13.0.92 requires numpy>=2, but you have numpy 1.26.4
```

**Nguyên nhân:** `ultralytics` kéo `numpy>=2` lên, trong khi `mediapipe` yêu cầu `numpy<2`. Hai package xung đột nhau.

**Cách tránh:** Luôn pin numpy SAU KHI cài ultralytics:
```bash
TMPDIR=~/pip_tmp pip install ultralytics
pip install "numpy>=1.26.4,<2" --force-reinstall  # Chạy ngay sau
pip uninstall opencv-python -y                     # Gỡ opencv pip nếu bị kéo vào
```

---

### LỖI 6 — `/tmp` đầy khi cài ultralytics

**Triệu chứng:**
```
ERROR: Could not install packages due to an OSError: [Errno 28] No space left on device
```

**Nguyên nhân:** `/tmp` chỉ có ~1.9GB (tmpfs), trong khi ultralytics kéo nhiều file NVIDIA/CUDA lớn (nvidia_cublas: 543MB, nvidia_cudnn: 434MB...) tổng >2GB vào `/tmp` trước khi cài.

**Cách tránh:** Luôn dùng `TMPDIR` trỏ về ổ chính khi cài ultralytics:
```bash
mkdir -p ~/pip_tmp
TMPDIR=~/pip_tmp pip install ultralytics
```

---

### LỖI 7 — `cv2.__file__` trả về `None` — cv2 là namespace rỗng

**Triệu chứng:**
```python
import cv2; print(cv2.__file__)  # → None
import cv2; print(dir(cv2))      # → chỉ có __doc__, __name__... không có cvtColor
```

**Nguyên nhân:** Không có binary cv2 nào trong venv. Python tìm thấy namespace package rỗng tên `cv2` thay vì OpenCV thật.

**Cách tránh:** Kiểm tra ngay sau khi cài:
```bash
find venv -name "cv2*.so"  # Phải thấy file .so
python3 -c "import cv2; print(cv2.__file__)"  # Phải có đường dẫn thật
```

---

### LỖI 8 — `python3-opencv` từ apt chỉ có binary cho Python 3.13

**Triệu chứng:**
```bash
find /usr -name "cv2*"
# → cv2.cpython-313-aarch64-linux-gnu.so  ← chỉ cp313, không có cp311
```

**Nguyên nhân:** Debian 13 build `python3-opencv` cho Python 3.13 (system default). Venv Python 3.11 không thể dùng trực tiếp file `.so` này.

**Cách tránh:** Dùng file `.pth` để thêm đường dẫn system vào `sys.path` của Python 3.11:
```bash
echo "/usr/lib/python3/dist-packages" > \
    venv/lib/python3.11/site-packages/system_cv2.pth
# Python 3.11 sẽ load cv2 từ system path — hoạt động vì ABI tương thích
```

---

## ✅ TRÌNH TỰ CÀI ĐẶT ĐÚNG (Từ đầu đến cuối)

```bash
# === PHASE 1: Chuẩn bị hệ thống ===
sudo apt update && sudo apt upgrade -y
sudo apt install -y make build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev curl \
    libncursesw5-dev xz-utils tk-dev libxml2-dev \
    libxmlsec1-dev libffi-dev liblzma-dev git \
    libgtk-3-dev libgtk2.0-dev pkg-config libglib2.0-0 \
    python3-opencv libopencv-dev

# === PHASE 2: Cài Python 3.11 qua pyenv ===
curl https://pyenv.run | bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init - bash)"' >> ~/.bashrc
source ~/.bashrc
pyenv install 3.11.9   # Mất 15-25 phút

# === PHASE 3: Tạo venv Python 3.11 ===
cd ~/Documents/ce_comedians/project
pyenv local 3.11.9
python3 --version      # Xác nhận: Python 3.11.9

rm -rf venv
python3 -m venv venv --system-site-packages
source venv/bin/activate

# === PHASE 4: Link cv2 từ apt vào venv ===
echo "/usr/lib/python3/dist-packages" > \
    venv/lib/python3.11/site-packages/system_cv2.pth

# Kiểm tra cv2
python3 -c "import cv2; print('cv2:', cv2.__version__, '| file:', cv2.__file__)"
# Mong đợi: cv2: 4.10.0 | file: /usr/lib/python3/dist-packages/cv2...

# Test imshow
python3 -c "
import cv2, numpy as np
img = np.zeros((300,400,3), dtype=np.uint8)
cv2.putText(img, 'TEST OK', (50,150), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,0), 3)
cv2.imshow('Test', img)
cv2.waitKey(2000)
cv2.destroyAllWindows()
print('imshow OK!')
"

# === PHASE 5: Cài numpy (pin version) ===
pip install --upgrade pip setuptools wheel
pip install "numpy>=1.26.4,<2"

# === PHASE 6: Cài mediapipe ===
pip install mediapipe \
    --find-links https://github.com/nickoala/mediapipe-on-raspberry-pi/releases/
# Phải thấy: mediapipe-0.10.18-cp311-cp311-linux_aarch64.whl

python3 -c "import mediapipe as mp; print('mediapipe:', mp.__version__)"

# === PHASE 7: Cài ultralytics ===
mkdir -p ~/pip_tmp
TMPDIR=~/pip_tmp pip install ultralytics

# Fix numpy bị kéo lên numpy 2.x
pip install "numpy>=1.26.4,<2" --force-reinstall
# Gỡ opencv-python bị kéo vào
pip uninstall opencv-python opencv-contrib-python opencv-python-headless -y

# === PHASE 8: Tải YOLO model ===
python3 -c "
from ultralytics import YOLO
model = YOLO('yolo11n.pt')
print('YOLO OK, classes:', len(model.names))
"

# === PHASE 9: Kiểm tra toàn bộ ===
python3 -c "
import cv2, mediapipe as mp, numpy as np
from ultralytics import YOLO
img = np.zeros((100,100,3), dtype=np.uint8)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
print('cv2      :', cv2.__version__)
print('mediapipe:', mp.__version__)
print('numpy    :', np.__version__)
print('cv2 test :', gray.shape)
print('=== TẤT CẢ OK ===')
"

# === PHASE 10: Chạy project ===
export DISPLAY=:0
python3 main.py
```

---

## 📊 BẢNG TỔNG HỢP: NÊN và KHÔNG NÊN

| | KHÔNG NÊN ❌ | NÊN ✅ |
|---|---|---|
| **Python version** | Python 3.13 (system default) | Python 3.11.9 (qua pyenv) |
| **MediaPipe** | `pip install mediapipe` thẳng | `--find-links nickoala/releases` |
| **MediaPipe** | `mediapipe-rpi4` (binary 32-bit) | `mediapipe-0.10.18-cp311-aarch64` |
| **OpenCV** | `pip install opencv-python` | `sudo apt install python3-opencv` + `.pth` file |
| **OpenCV** | `opencv-python-headless` | cv2 từ apt (có GTK, có imshow) |
| **NumPy** | Để mặc định (bị kéo lên 2.x) | Pin: `numpy>=1.26.4,<2` |
| **ultralytics** | `pip install ultralytics` thẳng | `TMPDIR=~/pip_tmp pip install ultralytics` |
| **Sau ultralytics** | Bỏ qua xung đột | `pip install numpy<2 --force-reinstall` ngay |
| **venv** | `python3 -m venv venv` | `python3 -m venv venv --system-site-packages` |

---

## 🔧 THÔNG TIN MÔI TRƯỜNG

```
Hardware  : Raspberry Pi 4
OS        : Debian GNU/Linux 13 (trixie)
Arch      : ARM64 (aarch64)
Kernel    : Linux 6.12.75+rpt-rpi-v8
Camera    : Webcam USB (CAMERA_INDEX = 0)
Python    : 3.11.9 (pyenv) — KHÔNG dùng 3.13 system
cv2       : 4.10.0 (apt: python3-opencv) — KHÔNG dùng pip
mediapipe : 0.10.18 (community wheel cp311-aarch64)
numpy     : 1.26.4 (pinned <2)
ultralytics: 8.4.48
```

---

## ⚡ WARNINGS BÌNH THƯỜNG — KHÔNG CẦN XỬ LÝ

Các dòng sau xuất hiện khi chạy là **bình thường**, không phải lỗi:

```
Error in cpuinfo: prctl(PR_SVE_GET_VL) failed
INFO: Created TensorFlow Lite XNNPACK delegate for CPU.
W0000 inference_feedback_manager.cc: Feedback manager requires a model with a single signature
W0000 landmark_projection_calculator.cc: Using NORM_RECT without IMAGE_DIMENSIONS
QStandardPaths: wrong permissions on runtime directory /run/user/1000
(python3): GLib-GObject-CRITICAL: g_object_unref: assertion 'G_IS_OBJECT (object)' failed
```

Fix permission warning (một lần duy nhất):
```bash
chmod 700 /run/user/1000
```


Lỗi cần tránh:
phat@phat:~/Documents/ce_comedians/project $ python3 -c "import cv2; print(cv2.__version__)"
4.10.0
phat@phat:~/Documents/ce_comedians/project $ curl https://pyenv.run | bash
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   270  100   270    0     0    188      0  0:00:01  0:00:01 --:--:--   188
WARNING: Can not proceed with installation. Kindly remove the '/home/phat/.pyenv' directory first.
phat@phat:~/Documents/ce_comedians/project $ echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init - bash)"' >> ~/.bashrc
source ~/.bashrc
phat@phat:~/Documents/ce_comedians/project $ pyenv install 3.11.9
pyenv: /home/phat/.pyenv/versions/3.11.9 already exists
continue with installation? (y/N) y
Downloading Python-3.11.9.tar.xz...
-> https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tar.xz
Installing Python-3.11.9...
patching file setup.py
Installed Python-3.11.9 to /home/phat/.pyenv/versions/3.11.9
phat@phat:~/Documents/ce_comedians/project $ cd ~/Documents/ce_comedians/project
pyenv local 3.11.9
phat@phat:~/Documents/ce_comedians/project $ python3 --version
Python 3.11.9
phat@phat:~/Documents/ce_comedians/project $ cd ~/Documents/ce_comedians/project
python3 -m venv venv --system-site-packages
source venv/bin/activate
(venv) phat@phat:~/Documents/ce_comedians/project $ python3 --version
Python 3.11.9
(venv) phat@phat:~/Documents/ce_comedians/project $ which python3
/home/phat/Documents/ce_comedians/project/venv/bin/python3
(venv) phat@phat:~/Documents/ce_comedians/project $ echo "/usr/lib/python3/dist-packages" > \
    venv/lib/python3.11/site-packages/system_cv2.pth
(venv) phat@phat:~/Documents/ce_comedians/project $ python3 -c "import cv2; print('cv2:', cv2.__version__, '| file:', cv2.__file__)"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'cv2'


(venv) phat@phat:~/Documents/ce_comedians/project $ find /usr/lib/python3/dist-packages -name "cv2*"
/usr/lib/python3/dist-packages/cv2.cpython-313-aarch64-linux-gnu.so
(venv) phat@phat:~/Documents/ce_comedians/project $ df -h /
Filesystem      Size  Used Avail Use% Mounted on
/dev/mmcblk0p2   29G  9.6G   18G  35% /

(venv) phat@phat:~/Documents/ce_comedians/project $ deactivate
sudo apt install -y \
    cmake ninja-build \
    libjpeg-dev libpng-dev libtiff-dev \
    libavcodec-dev libavformat-dev libswscale-dev \
    libv4l-dev v4l-utils \
    libxvidcore-dev libx264-dev \
    libgtk-3-dev libgtk2.0-dev \
    libatlas-base-dev gfortran \
    libhdf5-dev libhdf5-serial-dev \
    python3-dev
Note, selecting 'libhdf5-dev' instead of 'libhdf5-serial-dev'
Package libatlas-base-dev is not available, but is referred to by another package.
This may mean that the package is missing, has been obsoleted, or
is only available from another source
Error: Package 'libatlas-base-dev' has no installation candidate
phat@phat:~/Documents/ce_comedians/project $

Illegal instruction — opencv-python 4.11 từ PyPI vẫn dùng CPU instructions không có trên ARM Cortex-A72. Phải quay lại dùng cv2 từ apt nhưng theo cách khác: build wrapper nhỏ để Python 3.11 load được file .so của cp313


# KINH NGHIỆM BỔ SUNG — Debug Session 2
> Raspberry Pi 4 · Debian GNU/Linux 13 (trixie) · ARM64 · Python 3.11.9 · pyenv venv

---

## ⚠️ LỖI 9 — `Illegal instruction` khi `model.predict()` với PyTorch mới trên Pi 4

### Triệu chứng

```
Illegal instruction
```

Xuất hiện **ngay sau dòng** `model.predict(frame, verbose=False)` khi chạy YOLO inference. Không crash ở import, không crash ở load model, chỉ crash khi inference thực sự chạy.

### Cách xác định thủ phạm (quy trình debug đúng)

Không nên chạy thẳng `python3 main.py` rồi đoán lỗi. Phải **cô lập từng thành phần**:

**Bước 1:** Test cv2 + imshow độc lập
```bash
DISPLAY=:0 python3 -c "
import cv2, numpy as np
img = np.zeros((300,400,3), dtype=np.uint8)
cv2.imshow('Test', img)
cv2.waitKey(2000)
cv2.destroyAllWindows()
print('imshow OK!')
"
```

**Bước 2:** Test mediapipe + cv2 + webcam cùng nhau
```bash
DISPLAY=:0 python3 -c "
import cv2, numpy as np, mediapipe as mp
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True,
    min_detection_confidence=0.5, min_tracking_confidence=0.5)
cap = cv2.VideoCapture(0)
ok, frame = cap.read()
cap.release()
rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
results = face_mesh.process(rgb)
print('face_mesh.process OK')
cv2.imshow('Test', np.zeros((300,400,3), dtype=np.uint8))
cv2.waitKey(1000)
cv2.destroyAllWindows()
print('imshow after mediapipe OK')
"
```

**Bước 3:** Test YOLO predict (thêm ultralytics vào)
```bash
DISPLAY=:0 python3 -c "
import cv2, numpy as np, mediapipe as mp
from ultralytics import YOLO
model = YOLO('yolo11n.pt')
cap = cv2.VideoCapture(0)
ok, frame = cap.read()
cap.release()
results = model.predict(frame, verbose=False)
print('YOLO predict OK')
"
```

→ **Nếu crash ở Bước 3 mà Bước 1+2 OK**: thủ phạm là PyTorch/ultralytics, không phải cv2 hay mediapipe.

### Nguyên nhân gốc rễ

`ultralytics 8.x` kéo `torch 2.11.0` + `triton 3.6.0` vào. Các binary này được compile với CPU instructions (có thể là NEON extensions nặng hoặc các flags khác) **không có trên ARM Cortex-A72 của Pi 4**.

PyTorch chính thức **không còn build wheel riêng cho Raspberry Pi** từ torch 2.x trở đi.

```bash
# Kiểm tra torch version và CPU capability
python3 -c "import torch; print(torch.__version__); print(torch.backends.cpu.get_cpu_capability())"
```

### Các hướng giải quyết (chưa xác nhận — cần tiếp tục)

> ⚠️ Session này kết thúc trước khi giải pháp được triển khai xong. Ba hướng đang xem xét:

| Hướng | Mô tả | Đánh đổi |
|---|---|---|
| **A — Tắt phone detection** | Đặt `USE_PHONE_DETECTION = False` trong `main.py` | Mất tính năng phát hiện điện thoại; chạy được ngay |
| **B — Dùng torch cũ hơn cho Pi 4** | Tìm community wheel `torch` tương thích Cortex-A72, pin version | Cần tìm đúng version; có thể phải dùng `torch<=1.13` hoặc build from source |
| **C — Export YOLO sang ONNX** | Export `yolo11n.pt` → `yolo11n.onnx` trên máy x86, copy sang Pi, dùng `onnxruntime` thay PyTorch | Cần máy x86 để export; `onnxruntime` có wheel cho aarch64 |

---

## 📋 TRẠNG THÁI MÔI TRƯỜNG KHI KẾT THÚC SESSION NÀY

Đây là cấu hình đang hoạt động (trừ YOLO inference):

```
Python   : 3.11.9 (pyenv)
cv2      : 4.11.0.86 (pip, opencv-python — imshow OK với DISPLAY=:0)
mediapipe: 0.10.18 (community wheel cp311-aarch64)
numpy    : 1.26.4 (pinned <2)
ultralytics: 8.4.48 (torch 2.11.0 — predict() CRASH Illegal instruction)
```

**Lệnh kiểm tra nhanh toàn bộ môi trường:**
```bash
python3 -c "
import cv2, mediapipe as mp, numpy as np
import ultralytics
print('cv2      :', cv2.__version__)
print('mediapipe:', mp.__version__)
print('numpy    :', np.__version__)
print('ultralytics:', ultralytics.__version__)
import torch; print('torch    :', torch.__version__)
"
```

---

## 🔎 QUAN SÁT QUAN TRỌNG VỀ NUMPY CONFLICT

Trong session này phát hiện một pattern lặp lại:

```
# opencv-python 4.13 yêu cầu numpy>=2
# mediapipe 0.10.18 yêu cầu numpy<2
# ultralytics kéo numpy lên 2.4.4 mỗi khi cài
```

**Giải pháp tạm thời đã hoạt động:**
1. Cài `opencv-python==4.11.0.86` (version cũ hơn, không yêu cầu numpy>=2)
2. Pin numpy: `pip install "numpy>=1.26.4,<2" --force-reinstall`
3. **Không** cài lại opencv sau khi pin numpy

**Thứ tự cài đặt quan trọng:**
```bash
pip install "opencv-python==4.11.0.86"
pip install mediapipe --find-links https://github.com/nickoala/mediapipe-on-raspberry-pi/releases/
TMPDIR=~/pip_tmp pip install ultralytics
pip install "numpy>=1.26.4,<2" --force-reinstall
# KHÔNG chạy pip install opencv-python sau bước này
```

---

## ⚡ WARNING BỔ SUNG — BÌNH THƯỜNG, KHÔNG CẦN XỬ LÝ

```
qt.qpa.plugin: Could not find the Qt platform plugin "wayland" in ".../cv2/qt/plugins"
```

Xuất hiện khi `opencv-python` từ pip dùng Qt backend. **Không ảnh hưởng** đến hoạt động của `cv2.imshow()` — cửa sổ vẫn hiện bình thường qua X11/xcb. Bỏ qua warning này.

---

## 📌 GHI CHÚ CHO LẦN TRIỂN KHAI TIẾP THEO

Trước khi bắt đầu, cần trả lời 3 câu hỏi:

1. **Phone detection có bắt buộc không?** Nếu không → `USE_PHONE_DETECTION = False`, bỏ qua toàn bộ ultralytics/torch.
2. **Có máy x86 để export ONNX không?** Nếu có → dùng hướng C (onnxruntime), tránh được PyTorch hoàn toàn.
3. **Chạy lệnh này để xác nhận torch có hoạt động không:**
```bash
python3 -c "
import torch, numpy as np
x = torch.from_numpy(np.zeros((1,3,640,640), dtype=np.float32))
y = x * 2
print('torch CPU inference OK:', y.shape)
"
```
Nếu lệnh trên crash `Illegal instruction` → PyTorch không dùng được trên Pi 4 này với version hiện tại, phải chuyển sang ONNX hoặc tắt phone detection.
