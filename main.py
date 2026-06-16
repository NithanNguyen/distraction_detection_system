import os

# ==============================================================================
# 0. CHẶN CẢNH BÁO HỆ THỐNG & TỐI ƯU HÓA GPU (Đặt trên cùng)
# ==============================================================================
os.environ["QT_QPA_PLATFORM"]        = "xcb"   # Sửa lỗi Qt Wayland plugin
os.environ["GLOG_minloglevel"]        = "3"     # Tắt nhật ký MediaPipe
os.environ["TF_CPP_MIN_LOG_LEVEL"]   = "3"     # Tắt nhật ký TensorFlow
os.environ["ONNXRUNTIME_DISABLE_GPU"] = "1"    # Không dùng GPU cảnh báo ONNX
os.environ["CUDA_VISIBLE_DEVICES"]   = "-1"    # Ẩn thiết bị CUDA
os.environ["MEDIAPIPE_DISABLE_GPU"]  = "1"     # Buộc chạy MediaPipe trên CPU

import cv2
import mediapipe as mp
import numpy as np
import time
import math
import platform
import signal
import sys
import socket
import threading
import requests
import main_gpio_alert  # Driver LED vàng + buzzer (xem README_DEPLOY.md muc 4.1)

# ==============================================================================
# 1. CẤU HÌNH BLYNK
# ==============================================================================
BLYNK_AUTH_TOKEN = "0cS7u48kkbPHi_iecesgzfkIrjOFAUf5"

# ==============================================================================
# 2. NGƯỠNG HÀNH VI GIÁM SÁT
# ==============================================================================
CAMERA_INDEX = 0
USE_PHONE_DETECTION = True

# TC-002: Chỉ xuất hiện một phần
PARTIAL_FACE_MARGIN_PX = 25
PARTIAL_FACE_SECONDS = 1.0

# TC-003: Cúi đầu nhặt đồ
PICK_OBJECT_SECONDS = 1.0
PICK_HEAD_DROP_THRESHOLD = 28.0

# Ngưỡng mắt / miệng / tư thế đầu
EAR_THRESHOLD = 0.20
MAR_THRESHOLD = 0.50
EYE_CLOSED_SECONDS = 1.3
YAWN_SECONDS = 1.0
DISTRACT_SECONDS = 4.5
NO_FACE_SECONDS = 2.0
ALERT_COOLDOWN_SECONDS = 2.0

TILT_THRESHOLD = 25.0
SHAKE_THRESHOLD = 15.0
SHAKE_COUNT_LIMIT = 3
MOVE_SPEED_THRESHOLD = 0.15

# Tối ưu Head Pose
CALIBRATION_SECONDS = 2.0
HEAD_POSE_ALPHA = 0.25
MAX_ANGLE_JUMP = 20.0
MIN_FACE_BOX_SIZE = 120
YAW_ENTER_THRESHOLD = 20.0
YAW_EXIT_THRESHOLD = 15.0
PITCH_ENTER_THRESHOLD = 20.0
PITCH_EXIT_THRESHOLD = 12.0
HEAD_DROP_SIGN = 1

# Phát hiện điện thoại
PHONE_MODEL_PATH = "yolo11n.onnx"
PHONE_CONF_THRESHOLD = 0.45
PHONE_USE_SECONDS = 1.5
PHONE_DETECT_EVERY_N_FRAMES = 4
PHONE_IOU_WITH_FACE_THRESHOLD = 0.02
PHONE_NEAR_FACE_EXPAND_PX = 180

# Ánh sáng
LOW_LIGHT_BRIGHTNESS_THRESHOLD = 60
LOW_LIGHT_NOISE_THRESHOLD = 15
LOW_LIGHT_SECONDS = 1.5
LIGHT_CHECK_EVERY_N_FRAMES = 10
CAMERA_RETRY_LIMIT = 5

LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]
MOUTH_TOP_BOTTOM = [(13, 14), (81, 178), (311, 402)]
MOUTH_LEFT_RIGHT = (78, 308)
HEAD_POSE_LANDMARKS = {
    "nose_tip": 1, "chin": 152,
    "left_eye_outer": 33, "right_eye_outer": 263,
    "mouth_left": 61, "mouth_right": 291
}

# ==============================================================================
# 3. BIẾN TOÀN CỤC TRẠNG THÁI
# ==============================================================================
count1 = 0  # V1: Buồn ngủ
count2 = 0  # V2: Nhìn lệch
count3 = 0  # V3: Vắng mặt
count4 = 0  # V4: Sử dụng điện thoại
count5 = 0  # V5: Hành vi bất thường

system_state = "RUNNING"
cap = None
blynk = None
blynk_enabled = False
status = "Tap trung"

# ==============================================================================
# 4. BLYNK HTTP ADAPTER — thay the blynklib, tuong thich voi Blynk IoT 2.0
# ==============================================================================
class BlynkHTTP:
    """
    Gửi dữ liệu lên Blynk IoT 2.0 qua HTTPS REST API.
    Interface giống blynklib (connected / run / virtual_write) nên
    phần còn lại của code không cần thay đổi.
    """
    BASE_URL = "https://blynk.cloud/external/api"

    def __init__(self, token: str):
        self.token = token

    def connected(self) -> bool:
        """HTTP là stateless — luôn sẵn sàng gửi."""
        return True

    def run(self) -> None:
        """No-op: HTTP không cần vòng lặp keep-alive."""
        pass

    def virtual_write(self, pin: int, value) -> None:
        """Gửi giá trị lên Virtual Pin trong thread riêng để không block main loop."""
        def _send():
            try:
                url = f"{self.BASE_URL}/update?token={self.token}&V{pin}={value}"
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    print(f"[BLYNK HTTP] V{pin} = {value} -> OK")
                else:
                    print(f"[BLYNK HTTP] V{pin} loi: HTTP {r.status_code} | {r.text.strip()}")
            except requests.exceptions.Timeout:
                print(f"[BLYNK HTTP] V{pin} timeout (>5s) — kiem tra mang.")
            except Exception as e:
                print(f"[BLYNK HTTP] V{pin} exception: {e}")
        threading.Thread(target=_send, daemon=True).start()

# ==============================================================================
# 5. HÀM BỔ TRỢ HỆ THỐNG
# ==============================================================================
def signal_handler(sig, frame):
    global system_state
    print(f"\n[SIGNAL] Nhan duoc tin hieu {sig}. Dang chuyen sang trang thai SAVING_DATA...")
    system_state = "SAVING_DATA"
    raise KeyboardInterrupt


def check_internet():
    """Kiểm tra xem Raspberry Pi có đang online hay không."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False


def play_alert():
    try:
        if platform.system().lower().startswith("win"):
            import winsound
            winsound.Beep(1500, 250)
        else:
            print("\a", end="", flush=True)
    except Exception:
        pass


def check_lighting(frame, brightness_threshold=60, noise_threshold=15):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean = gray.mean()
    std = gray.std()
    too_dark = mean < brightness_threshold
    too_noisy = (mean < 90) and (std < noise_threshold)
    return too_dark or too_noisy, mean, std


def dist(p1, p2):
    return float(np.linalg.norm(np.array(p1, dtype=np.float64) - np.array(p2, dtype=np.float64)))


def eye_aspect_ratio(eye_points):
    p1, p2, p3, p4, p5, p6 = eye_points
    vertical_1 = dist(p2, p6)
    vertical_2 = dist(p3, p5)
    horizontal = dist(p1, p4)
    if horizontal == 0:
        return 0.0
    return (vertical_1 + vertical_2) / (2.0 * horizontal)


def mouth_aspect_ratio(face_points):
    w = dist(face_points[MOUTH_LEFT_RIGHT[0]], face_points[MOUTH_LEFT_RIGHT[1]])
    if w == 0:
        return 0.0
    v = sum(dist(face_points[a], face_points[b]) for a, b in MOUTH_TOP_BOTTOM) / len(MOUTH_TOP_BOTTOM)
    return v / w


def normalize_angle(angle):
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return float(angle)


def smooth_value(prev_val, new_val, alpha=0.25):
    if prev_val is None:
        return float(new_val)
    return float(alpha * new_val + (1 - alpha) * prev_val)


def clamp_angle_jump(prev_val, new_val, max_jump=20.0):
    if prev_val is None:
        return float(new_val)
    delta = normalize_angle(new_val - prev_val)
    delta = max(-max_jump, min(max_jump, delta))
    return float(prev_val + delta)


def rotation_matrix_to_euler_angles(R):
    sy = math.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])
    singular = sy < 1e-6
    if not singular:
        x = math.atan2(R[2, 1], R[2, 2])
        y = math.atan2(-R[2, 0], sy)
        z = math.atan2(R[1, 0], R[0, 0])
    else:
        x = math.atan2(-R[1, 2], R[1, 1])
        y = math.atan2(-R[2, 0], sy)
        z = 0
    return np.degrees(np.array([x, y, z], dtype=np.float64))


def get_face_box(face_points):
    xs = [p[0] for p in face_points]
    ys = [p[1] for p in face_points]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    return x_min, y_min, x_max, y_max, (x_max - x_min), (y_max - y_min)


def box_iou(boxA, boxB):
    ax1, ay1, ax2, ay2 = boxA
    bx1, by1, bx2, by2 = boxB
    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - inter_area
    return inter_area / union if union > 0 else 0.0


def expand_box(box, expand_px, frame_w, frame_h):
    x1, y1, x2, y2 = box
    return (
        max(0, int(x1 - expand_px)),
        max(0, int(y1 - expand_px)),
        min(frame_w - 1, int(x2 + expand_px)),
        min(frame_h - 1, int(y2 + expand_px))
    )


def center_in_box(point, box):
    x, y = point
    x1, y1, x2, y2 = box
    return x1 <= x <= x2 and y1 <= y <= y2


def is_partial_face(face_box, frame_w, frame_h, margin_px=25):
    if face_box is None:
        return False
    x1, y1, x2, y2 = face_box
    return x1 <= margin_px or y1 <= margin_px or x2 >= frame_w - margin_px or y2 >= frame_h - margin_px


def estimate_head_pose(face_points, frame_width, frame_height, prev_rvec=None, prev_tvec=None):
    image_points = np.array([
        face_points[HEAD_POSE_LANDMARKS["nose_tip"]],
        face_points[HEAD_POSE_LANDMARKS["chin"]],
        face_points[HEAD_POSE_LANDMARKS["left_eye_outer"]],
        face_points[HEAD_POSE_LANDMARKS["right_eye_outer"]],
        face_points[HEAD_POSE_LANDMARKS["mouth_left"]],
        face_points[HEAD_POSE_LANDMARKS["mouth_right"]],
    ], dtype=np.float64)

    model_points = np.array([
        (0.0, 0.0, 0.0),
        (0.0, -63.6, -12.5),
        (-43.3, 32.7, -26.0),
        (43.3, 32.7, -26.0),
        (-28.9, -28.9, -24.1),
        (28.9, -28.9, -24.1),
    ], dtype=np.float64)

    focal_length = frame_width
    center = (frame_width / 2.0, frame_height / 2.0)
    camera_matrix = np.array(
        [[focal_length, 0, center[0]],
         [0, focal_length, center[1]],
         [0, 0, 1]], dtype=np.float64
    )
    dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    if prev_rvec is not None and prev_tvec is not None:
        success, rotation_vec, translation_vec = cv2.solvePnP(
            model_points, image_points, camera_matrix, dist_coeffs,
            prev_rvec, prev_tvec, True, cv2.SOLVEPNP_ITERATIVE
        )
    else:
        success, rotation_vec, translation_vec = cv2.solvePnP(
            model_points, image_points, camera_matrix, dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )

    if not success:
        return None

    rotation_mat, _ = cv2.Rodrigues(rotation_vec)
    pitch, yaw, roll = rotation_matrix_to_euler_angles(rotation_mat)
    pitch = normalize_angle(pitch)
    yaw = normalize_angle(yaw)
    roll = normalize_angle(roll)

    nose_end_point2d, _ = cv2.projectPoints(
        np.array([(0.0, 0.0, 1000.0)], dtype=np.float64),
        rotation_vec, translation_vec, camera_matrix, dist_coeffs
    )
    return {
        "pitch": float(pitch), "yaw": float(yaw), "roll": float(roll),
        "nose_tip": tuple(map(int, image_points[0])),
        "nose_direction": tuple(map(int, nose_end_point2d[0][0])),
        "rvec": rotation_vec, "tvec": translation_vec
    }


def put_status_text(frame, status, color=(0, 255, 0)):
    cv2.rectangle(frame, (10, 10), (760, 95), (0, 0, 0), -1)
    cv2.putText(frame, f"Trang thai: {status}", (20, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    cv2.putText(frame, "Nhan Q de thoat", (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1)


def median_of_tuples(data):
    arr = np.array(data, dtype=np.float64)
    return np.median(arr[:, 0]), np.median(arr[:, 1]), np.median(arr[:, 2])


def load_phone_model():
    if not USE_PHONE_DETECTION:
        return None, {}
    try:
        import onnxruntime as ort
        import ast
        session = ort.InferenceSession(PHONE_MODEL_PATH, providers=["CPUExecutionProvider"])
        meta = session.get_modelmeta().custom_metadata_map
        names = ast.literal_eval(meta["names"]) if "names" in meta else {}
        return session, names
    except Exception as e:
        print(f"[WARN] Khong tai duoc model phone: {e}")
        return None, {}


def detect_phone(model, frame_bgr):
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
        scale_x, scale_y = orig_w / 640.0, orig_h / 640.0

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
            detections.append({"box": (x1, y1, x2, y2), "conf": conf, "label": "cell phone"})
    except Exception as e:
        print(f"[WARN] Loi detect phone: {e}")
    return detections


def is_phone_usage(phone_dets, face_box, frame_w, frame_h):
    if not phone_dets or face_box is None:
        return False, None
    expanded_face = expand_box(face_box, PHONE_NEAR_FACE_EXPAND_PX, frame_w, frame_h)
    for det in phone_dets:
        phone_box = det["box"]
        iou = box_iou(phone_box, face_box)
        cx = (phone_box[0] + phone_box[2]) // 2
        cy = (phone_box[1] + phone_box[3]) // 2
        if center_in_box((cx, cy), expanded_face) or iou >= PHONE_IOU_WITH_FACE_THRESHOLD:
            return True, det
    return False, None

# ==============================================================================
# 6. CÁC HÀM TRUYỀN DỮ LIỆU BLYNK
# ==============================================================================
def send_data_to_blynk(blynk_obj, is_enabled, current_status):
    """Gửi toàn bộ dữ liệu cuối cùng lên Blynk trước khi thoát chương trình."""
    global count1, count2, count3, count4, count5

    print("\n" + "=" * 60)
    print("[BLYNK] DANG GUI DU LIEU CUOI CUNG TRUOC KHI THOAT...")
    print(f"  - Pin V0 (Trang thai): {current_status}")
    print(f"  - Pin V1 (Buon ngu):   {count1}")
    print(f"  - Pin V2 (Nhin lech):  {count2}")
    print(f"  - Pin V3 (Vang mat):   {count3}")
    print(f"  - Pin V4 (Dien thoai): {count4}")
    print(f"  - Pin V5 (Bat thuong): {count5}")
    print("=" * 60)

    if not is_enabled or blynk_obj is None:
        print("[BLYNK] Blynk khong duoc cau hinh hoac bi tat.")
        return

    try:
        print("[BLYNK HTTP] Dang gui du lieu cuoi cung...")
        blynk_obj.virtual_write(0, current_status)
        blynk_obj.virtual_write(1, count1)
        blynk_obj.virtual_write(2, count2)
        blynk_obj.virtual_write(3, count3)
        blynk_obj.virtual_write(4, count4)
        blynk_obj.virtual_write(5, count5)
        # Cho toi da 6 giay de cac thread HTTP hoan thanh
        time.sleep(6.0)
        print("[BLYNK HTTP] Gui du lieu cuoi cung hoan tat!")
    except Exception as e:
        print(f"[ERROR] Loi gui du lieu cuoi cung: {e}")


def increment_counter(pin, blynk_obj, is_enabled):
    """Tăng biến đếm và gửi thời gian thực lên Blynk."""
    global count1, count2, count3, count4, count5
    val = 0
    if pin == 1:
        count1 += 1
        val = count1
    elif pin == 2:
        count2 += 1
        val = count2
    elif pin == 3:
        count3 += 1
        val = count3
    elif pin == 4:
        count4 += 1
        val = count4
    elif pin == 5:
        count5 += 1
        val = count5

    if is_enabled and blynk_obj is not None:
        try:
            if blynk_obj.connected():
                blynk_obj.virtual_write(pin, val)
                print(f"[BLYNK Real-time] Da gui V{pin} = {val}")
        except Exception as e:
            print(f"[BLYNK] Loi gui thoi gian thuc V{pin}: {e}")

# ==============================================================================
# 7. TIẾN TRÌNH CHÍNH (MAIN FUNCTION)
# ==============================================================================
def main():
    global system_state, cap, blynk, blynk_enabled, status
    global count1, count2, count3, count4, count5

    # Đăng ký Signal OS để dọn dẹp hệ thống khi tắt
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Kiểm tra Internet trước khi khởi tạo Blynk
    if not check_internet():
        print("[ERROR] Raspberry Pi khong co internet")
        return

    last_blynk_status = ""
    last_blynk_send_time = time.time()

    # ------------------------------------------------------------------
    # Khởi tạo Blynk qua HTTP REST API (thay the blynklib)
    # ------------------------------------------------------------------
    if BLYNK_AUTH_TOKEN not in ["", "YOUR_BLYNK_AUTH_TOKEN"]:
        try:
            blynk = BlynkHTTP(BLYNK_AUTH_TOKEN)
            blynk_enabled = True
            print("[BLYNK HTTP] Khoi tao HTTP adapter thanh cong.")
            print("[BLYNK HTTP] Du lieu se duoc gui len blynk.cloud qua HTTPS REST API.")
        except Exception as e:
            print(f"[BLYNK HTTP] Loi khoi tao: {e}")
            blynk_enabled = False
            blynk = None
    else:
        print("[WARN] Chua cau hinh BLYNK_AUTH_TOKEN")

    # ==========================================================================
    # Khởi tạo camera và model
    # ==========================================================================
    mp_face_mesh = mp.solutions.face_mesh
    phone_model, _ = load_phone_model()

    # Sử dụng CAP_V4L2 tối ưu cho driver camera trên Raspberry Pi
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise RuntimeError("Khong mo duoc webcam. Kiem tra CAMERA_INDEX hoac quyen camera.")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # Đọc thử frame đầu để cảnh báo nếu phòng tối
    ok_startup, startup_frame = cap.read()
    if ok_startup:
        is_low_startup, mean_startup, std_startup = check_lighting(
            startup_frame, LOW_LIGHT_BRIGHTNESS_THRESHOLD, LOW_LIGHT_NOISE_THRESHOLD
        )
        if is_low_startup:
            print(f"[CANH BAO] Anh sang yeu. mean={mean_startup:.0f}, std={std_startup:.0f}")

    # ===== BIẾN THỜI GIAN THEO DÕI TRẠNG THÁI =====
    eye_closed_since = None
    yawn_since = None
    distracted_since = None
    no_face_since = None
    tilt_since = None
    yaw_history = []
    prev_face_center = None
    move_since = None
    last_frame_time = time.time()
    phone_since = None
    low_light_since = None
    last_alert_time = 0.0
    partial_face_since = None
    pick_object_since = None
    is_low_light = False
    light_mean = 0.0
    light_std = 0.0

    # ===== HEAD POSE STATE (TƯ THẾ ĐẦU) =====
    prev_rvec = None
    prev_tvec = None
    smooth_pitch = None
    smooth_yaw = None
    smooth_roll = None
    base_pitch = None
    base_yaw = None
    base_roll = None
    calibration_start = None
    calibration_samples = []

    # ===== HYSTERESIS STATE (TRÁNH DAO ĐỘNG CẬP RẬP) =====
    distracted_state = False
    head_drop_state = False
    camera_fail_count = 0

    # ===== BIẾN FPS =====
    frame_count = 0
    cached_phone_dets = []
    fps_start = time.time()
    fps_counter = 0
    fps_display = 0.0

    # ===== TRẠNG THÁI CẢNH BÁO ĐỂ CHỐNG TỰ TĂNG BỘ ĐẾM =====
    state_eye_closed_alert = False
    state_yawn_alert = False
    state_head_drop_drowsy_alert = False
    state_distracted_alert = False
    state_no_face_alert = False
    state_phone_alert = False
    state_partial_face_alert = False
    state_pick_object_alert = False
    state_tilt_alert = False
    state_move_alert = False

    with mp_face_mesh.FaceMesh(
        max_num_faces=1, refine_landmarks=True,
        min_detection_confidence=0.5, min_tracking_confidence=0.5
    ) as face_mesh:

        while system_state == "RUNNING":
            # BlynkHTTP.run() la no-op — giu lai de giu cu phap tuong thich
            if blynk_enabled and blynk is not None:
                blynk.run()

            ok, frame = cap.read()
            if not ok or frame is None:
                camera_fail_count += 1
                if camera_fail_count >= CAMERA_RETRY_LIMIT:
                    print("[ERROR] Mat ket noi camera. Dang thu ket noi lai...")
                    cap.release()
                    time.sleep(2.0)
                    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)
                    camera_fail_count = 0
                    if not cap.isOpened():
                        print("[ERROR] Khong the ket noi lai camera. Thoat.")
                        break
                continue

            camera_fail_count = 0
            frame = cv2.flip(frame, 1)
            frame_h, frame_w = frame.shape[:2]
            now = time.time()

            # Định kỳ kiểm tra ánh sáng để giảm tải CPU
            if frame_count % LIGHT_CHECK_EVERY_N_FRAMES == 0:
                is_low_light, light_mean, light_std = check_lighting(
                    frame, LOW_LIGHT_BRIGHTNESS_THRESHOLD, LOW_LIGHT_NOISE_THRESHOLD
                )
            if is_low_light and low_light_since is None:
                low_light_since = now
            elif not is_low_light:
                low_light_since = None

            # Tính toán FPS hiển thị
            frame_count += 1
            fps_counter += 1
            if now - fps_start >= 1.0:
                fps_display = fps_counter / (now - fps_start)
                fps_counter, fps_start = 0, now

            # YOLO Phát hiện điện thoại định kỳ
            if USE_PHONE_DETECTION and phone_model is not None and frame_count % PHONE_DETECT_EVERY_N_FRAMES == 0:
                cached_phone_dets = detect_phone(phone_model, frame)

            # Xử lý FaceMesh phát hiện khuôn mặt
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)

            status = "Tap trung"
            status_color = (0, 255, 0)
            alert_messages = []
            ear, mar, pitch_rel, yaw_rel, roll_rel = 0.0, 0.0, 0.0, 0.0, 0.0
            current_face_box = None

            if results.multi_face_landmarks:
                no_face_since = None
                state_no_face_alert = False

                face_landmarks = results.multi_face_landmarks[0]
                face_points = [(lm.x * frame_w, lm.y * frame_h) for lm in face_landmarks.landmark]

                left_eye = [face_points[i] for i in LEFT_EYE_IDX]
                right_eye = [face_points[i] for i in RIGHT_EYE_IDX]
                ear = (eye_aspect_ratio(left_eye) + eye_aspect_ratio(right_eye)) / 2.0
                mar = mouth_aspect_ratio(face_points)

                x_min, y_min, x_max, y_max, box_w, box_h = get_face_box(face_points)
                face_size = min(box_w, box_h)
                current_face_box = (int(x_min), int(y_min), int(x_max), int(y_max))

                # TC-002: Chỉ xuất hiện một phần mặt ở rìa khung hình (Hành vi bất thường V5)
                partial_face_now = is_partial_face(current_face_box, frame_w, frame_h, PARTIAL_FACE_MARGIN_PX)
                if partial_face_now and partial_face_since is None:
                    partial_face_since = now
                elif not partial_face_now:
                    partial_face_since = None

                if partial_face_since is not None and (now - partial_face_since) >= PARTIAL_FACE_SECONDS:
                    alert_messages.append("HIEN DIEN: chi xuat hien mot phan trong khung hinh")
                    if not state_partial_face_alert:
                        increment_counter(5, blynk, blynk_enabled)
                        state_partial_face_alert = True
                else:
                    state_partial_face_alert = False

                # Ước lượng tư thế đầu (Head Pose)
                pose_valid = False
                if face_size >= MIN_FACE_BOX_SIZE:
                    pose = estimate_head_pose(face_points, frame_w, frame_h, prev_rvec, prev_tvec)
                    if pose is not None:
                        pose_valid = True
                        prev_rvec, prev_tvec = pose["rvec"], pose["tvec"]
                        raw_pitch = clamp_angle_jump(smooth_pitch, pose["pitch"], MAX_ANGLE_JUMP)
                        raw_yaw   = clamp_angle_jump(smooth_yaw,   pose["yaw"],   MAX_ANGLE_JUMP)
                        raw_roll  = clamp_angle_jump(smooth_roll,  pose["roll"],  MAX_ANGLE_JUMP)
                        smooth_pitch = smooth_value(smooth_pitch, raw_pitch, HEAD_POSE_ALPHA)
                        smooth_yaw   = smooth_value(smooth_yaw,   raw_yaw,   HEAD_POSE_ALPHA)
                        smooth_roll  = smooth_value(smooth_roll,  raw_roll,  HEAD_POSE_ALPHA)

                        # Hiệu chỉnh tư thế đầu lúc bắt đầu (Calibration)
                        if base_pitch is None or base_yaw is None or base_roll is None:
                            if calibration_start is None:
                                calibration_start = now
                                calibration_samples = []
                            calibration_samples.append((smooth_pitch, smooth_yaw, smooth_roll))
                            status = "Dang hieu chinh pose... giu dau thang"
                            status_color = (255, 255, 0)
                            if now - calibration_start >= CALIBRATION_SECONDS and len(calibration_samples) >= 15:
                                base_pitch, base_yaw, base_roll = median_of_tuples(calibration_samples)

                        if base_pitch is not None:
                            pitch_rel = normalize_angle(smooth_pitch - base_pitch)
                            yaw_rel   = normalize_angle(smooth_yaw   - base_yaw)
                            roll_rel  = normalize_angle(smooth_roll  - base_roll)
                        cv2.line(frame, pose["nose_tip"], pose["nose_direction"], (255, 255, 0), 2)
                    else:
                        prev_rvec, prev_tvec = None, None

                # Vẽ các điểm mốc chính lên khuôn mặt
                key_ids = sorted(set(
                    LEFT_EYE_IDX + RIGHT_EYE_IDX +
                    [p for pair in MOUTH_TOP_BOTTOM for p in pair] +
                    list(MOUTH_LEFT_RIGHT) +
                    list(HEAD_POSE_LANDMARKS.values())
                ))
                for idx in key_ids:
                    cv2.circle(frame, (int(face_points[idx][0]), int(face_points[idx][1])), 1, (0, 255, 255), -1)

                eye_closed = ear < EAR_THRESHOLD
                yawning    = mar > MAR_THRESHOLD

                if eye_closed and eye_closed_since is None:
                    eye_closed_since = now
                elif not eye_closed:
                    eye_closed_since = None

                if yawning and yawn_since is None:
                    yawn_since = now
                elif not yawning:
                    yawn_since = None

                distracted_now, head_drop_now = False, False
                if pose_valid and base_pitch is not None:
                    distracted_now = abs(yaw_rel) > (YAW_EXIT_THRESHOLD if distracted_state else YAW_ENTER_THRESHOLD)
                    head_drop_now  = (HEAD_DROP_SIGN * pitch_rel) > (PITCH_EXIT_THRESHOLD if head_drop_state else PITCH_ENTER_THRESHOLD)
                    distracted_state = distracted_now
                    head_drop_state  = head_drop_now

                    # Nghiêng đầu bất thường (Hành vi bất thường V5)
                    if abs(smooth_roll) > TILT_THRESHOLD:
                        if tilt_since is None:
                            tilt_since = now
                        elif (now - tilt_since) > 1.5:
                            alert_messages.append("CANH BAO: Nghieng dau bat thuong")
                            if not state_tilt_alert:
                                increment_counter(5, blynk, blynk_enabled)
                                state_tilt_alert = True
                    else:
                        tilt_since = None
                        state_tilt_alert = False

                    # Lắc đầu liên tục (Hành vi bất thường V5)
                    yaw_history.append((now, smooth_yaw))
                    yaw_history = [h for h in yaw_history if now - h[0] < 2.0]
                    if len(yaw_history) > 5:
                        shakes = 0
                        yaws = [h[1] for h in yaw_history]
                        last_peak, last_dir = yaws[0], 0
                        for val in yaws[1:]:
                            if abs(val - last_peak) > SHAKE_THRESHOLD:
                                current_dir = 1 if val > last_peak else -1
                                if last_dir != 0 and current_dir != last_dir:
                                    shakes += 1
                                last_dir, last_peak = current_dir, val
                        if shakes >= SHAKE_COUNT_LIMIT:
                            alert_messages.append("CANH BAO: Lac dau lien tuc")
                            if not state_tilt_alert:
                                increment_counter(5, blynk, blynk_enabled)
                            yaw_history = []

                    # Di chuyển vị trí khuôn mặt quá nhiều (Hành vi bất thường V5)
                    fx_center = (x_min + x_max) / 2.0 / frame_w
                    fy_center = (y_min + y_max) / 2.0 / frame_h
                    curr_center = (fx_center, fy_center)
                    is_moving = False
                    if prev_face_center is not None and now - last_frame_time > 0:
                        speed = math.sqrt(
                            (curr_center[0] - prev_face_center[0]) ** 2 +
                            (curr_center[1] - prev_face_center[1]) ** 2
                        ) / (now - last_frame_time)
                        if speed > MOVE_SPEED_THRESHOLD:
                            is_moving = True
                    prev_face_center = curr_center
                    last_frame_time = now

                    if is_moving:
                        if move_since is None:
                            move_since = now
                        elif (now - move_since) > 2.0:
                            alert_messages.append("CANH BAO: Di chuyen qua nhieu")
                            if not state_move_alert:
                                increment_counter(5, blynk, blynk_enabled)
                                state_move_alert = True
                    else:
                        move_since = None
                        state_move_alert = False

                    # TC-003: Cúi đầu nhặt đồ (Hành vi bất thường V5)
                    pick_object_now = (HEAD_DROP_SIGN * pitch_rel) > PICK_HEAD_DROP_THRESHOLD and ear >= EAR_THRESHOLD
                    if pick_object_now and pick_object_since is None:
                        pick_object_since = now
                    elif not pick_object_now:
                        pick_object_since = None

                    if pick_object_since is not None and (now - pick_object_since) >= PICK_OBJECT_SECONDS:
                        alert_messages.append("HIEN DIEN: cui xuong nhat do")
                        if not state_pick_object_alert:
                            increment_counter(5, blynk, blynk_enabled)
                            state_pick_object_alert = True
                    else:
                        state_pick_object_alert = False

                if distracted_now and distracted_since is None:
                    distracted_since = now
                elif not distracted_now:
                    distracted_since = None

                # Nhắm mắt quá lâu (Buồn ngủ V1)
                if eye_closed_since is not None and (now - eye_closed_since) >= EYE_CLOSED_SECONDS:
                    alert_messages.append("BUON NGU: nham mat qua lau")
                    if not state_eye_closed_alert:
                        increment_counter(1, blynk, blynk_enabled)
                        state_eye_closed_alert = True
                else:
                    state_eye_closed_alert = False

                # Ngáp (Buồn ngủ V1)
                if yawn_since is not None and (now - yawn_since) >= YAWN_SECONDS:
                    alert_messages.append("BUON NGU: phat hien ngap")
                    if not state_yawn_alert:
                        increment_counter(1, blynk, blynk_enabled)
                        state_yawn_alert = True
                else:
                    state_yawn_alert = False

                # Gục đầu nhắm mắt (Buồn ngủ V1)
                if head_drop_now and eye_closed_since is not None and (now - eye_closed_since) >= EYE_CLOSED_SECONDS:
                    alert_messages.append("BUON NGU: guc dau va nham mat")
                    if not state_head_drop_drowsy_alert:
                        increment_counter(1, blynk, blynk_enabled)
                        state_head_drop_drowsy_alert = True
                else:
                    state_head_drop_drowsy_alert = False

                # Nhìn lệch hướng (Mất tập trung V2)
                if distracted_since is not None and (now - distracted_since) >= DISTRACT_SECONDS:
                    alert_messages.append("MAT TAP TRUNG: nhin lech huong")
                    if not state_distracted_alert:
                        increment_counter(2, blynk, blynk_enabled)
                        state_distracted_alert = True
                else:
                    state_distracted_alert = False

                # Vẽ hộp giới hạn khuôn mặt
                cv2.rectangle(frame, (int(x_min), int(y_min)), (int(x_max), int(y_max)), (120, 120, 120), 1)

                # Debug overlay (EAR, MAR, góc tư thế đầu)
                cv2.putText(frame, f"EAR: {ear:.3f}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, f"MAR: {mar:.3f}", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, f"Pitch(rel): {pitch_rel:.1f}", (20, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, f"Yaw(rel): {yaw_rel:.1f}",   (20, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, f"Roll(rel): {roll_rel:.1f}", (20, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, f"Partial: {partial_face_now}", (20, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                if base_pitch is None:
                    cv2.putText(frame, "Dang hieu chinh pose: nhin thang vao camera",
                                (20, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            else:
                # Không thấy khuôn mặt trong khung hình — reset các biến trạng thái
                eye_closed_since = None
                yawn_since = None
                distracted_since = None
                partial_face_since = None
                pick_object_since = None
                prev_rvec = None
                prev_tvec = None
                smooth_pitch = None
                smooth_yaw = None
                smooth_roll = None
                distracted_state = False
                head_drop_state = False
                state_eye_closed_alert = False
                state_yawn_alert = False
                state_head_drop_drowsy_alert = False
                state_distracted_alert = False
                state_partial_face_alert = False
                state_pick_object_alert = False
                state_tilt_alert = False
                state_move_alert = False

                if no_face_since is None:
                    no_face_since = now

                # Vắng mặt (V3)
                if (now - no_face_since) >= NO_FACE_SECONDS:
                    status = "Mat tap trung (Khong thay khuon mat)"
                    status_color = (0, 165, 255)
                    alert_messages.append("MAT TAP TRUNG: khong phat hien khuon mat")
                    if not state_no_face_alert:
                        increment_counter(3, blynk, blynk_enabled)
                        state_no_face_alert = True
                else:
                    state_no_face_alert = False

            # Xử lý phát hiện điện thoại (V4)
            phone_in_use, phone_det_used = False, None
            if USE_PHONE_DETECTION and current_face_box is not None and len(cached_phone_dets) > 0:
                phone_in_use, phone_det_used = is_phone_usage(cached_phone_dets, current_face_box, frame_w, frame_h)

            if phone_in_use and phone_since is None:
                phone_since = now
            elif not phone_in_use:
                phone_since = None

            if phone_since is not None and (now - phone_since) >= PHONE_USE_SECONDS:
                alert_messages.append("MAT TAP TRUNG: dang su dung dien thoai")
                if not state_phone_alert:
                    increment_counter(4, blynk, blynk_enabled)
                    state_phone_alert = True
            else:
                state_phone_alert = False

            # Vẽ bounding box của điện thoại phát hiện được
            for det in cached_phone_dets:
                x1, y1, x2, y2 = det["box"]
                color = (0, 0, 255) if (phone_det_used is not None and det["box"] == phone_det_used["box"]) else (255, 0, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"Phone {det['conf']:.2f}", (x1, max(20, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Phân cấp trạng thái ưu tiên hiển thị lên UI
            has_drowsy    = any(msg.startswith("BUON NGU") for msg in alert_messages)
            has_phone     = any("dien thoai" in msg for msg in alert_messages)
            has_distracted = any(msg.startswith("MAT TAP TRUNG") for msg in alert_messages)
            has_presence  = any(msg.startswith("HIEN DIEN") for msg in alert_messages)

            if has_phone:
                status, status_color = "Dang dung dien thoai", (255, 0, 255)
            elif has_drowsy and has_distracted:
                status, status_color = "Buon ngu + Mat tap trung", (0, 0, 255)
            elif has_presence:
                status, status_color = "Hien dien khong hop le", (0, 165, 255)
            elif has_drowsy:
                status, status_color = "Buon ngu", (0, 0, 255)
            elif has_distracted:
                status, status_color = "Mat tap trung", (0, 165, 255)

            # Cảnh báo ánh sáng yếu
            low_light_active = low_light_since is not None and (now - low_light_since) >= LOW_LIGHT_SECONDS
            if low_light_active:
                alert_messages.clear()
                status = "Anh sang yeu - khong the giam sat"
                status_color = (0, 165, 255)

            # ===== DRIVE HARDWARE ALERT (LED vang + buzzer) =====
            main_gpio_alert.update(len(alert_messages) > 0)

            # ===== BLYNK STATUS REAL-TIME (V0) =====
            # Chỉ gửi khi trạng thái thay đổi để tiết kiệm băng thông
            if blynk_enabled and blynk is not None and status != last_blynk_status:
                try:
                    blynk.virtual_write(0, status)
                    last_blynk_status = status
                except Exception as e:
                    print(f"[BLYNK] Loi gui status V0: {e}")

            # ===== BLYNK PERIODIC SYNC (Đồng bộ toàn bộ V1-V5 mỗi 60 giây) =====
            if blynk_enabled and blynk is not None and (now - last_blynk_send_time) >= 60.0:
                try:
                    print("[BLYNK HTTP] Dang gui du lieu dinh ky 1 phut (V1-V5)...")
                    blynk.virtual_write(1, count1)
                    blynk.virtual_write(2, count2)
                    blynk.virtual_write(3, count3)
                    blynk.virtual_write(4, count4)
                    blynk.virtual_write(5, count5)
                    last_blynk_send_time = now
                except Exception as e:
                    print(f"[BLYNK] Loi gui du lieu dinh ky: {e}")

            # Vẽ UI overlay hiển thị chỉ số lên Frame
            put_status_text(frame, status, status_color)
            cv2.putText(frame, f"FPS: {fps_display:.1f}", (frame_w - 160, 42),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            # Bảng thống kê bộ đếm hành vi góc trên bên phải
            cv2.rectangle(frame, (frame_w - 290, 80),  (frame_w - 10, 260), (0, 0, 0), -1)
            cv2.rectangle(frame, (frame_w - 290, 80),  (frame_w - 10, 260), (0, 255, 255), 1)
            cv2.putText(frame, "BO DEM HANH VI:",       (frame_w - 270, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
            cv2.putText(frame, f"V1 (Buon ngu):   {count1}", (frame_w - 270, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, f"V2 (Nhin lech):  {count2}", (frame_w - 270, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, f"V3 (Khong mat):  {count3}", (frame_w - 270, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, f"V4 (Dien thoai): {count4}", (frame_w - 270, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, f"V5 (Bat thuong): {count5}", (frame_w - 270, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # Hiển thị tối đa 4 dòng thông tin cảnh báo ở góc dưới bên trái
            for i, msg in enumerate(alert_messages[:4]):
                color = (0, 0, 255) if msg.startswith("BUON NGU") else (
                    (255, 0, 255) if "dien thoai" in msg else (0, 165, 255)
                )
                cv2.putText(frame, msg, (20, 330 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            if low_light_active:
                cv2.rectangle(frame, (0, frame_h - 60), (frame_w, frame_h), (0, 0, 0), -1)
                cv2.putText(frame,
                            f"CANH BAO: Anh sang yeu (mean={light_mean:.0f}, std={light_std:.0f})",
                            (20, frame_h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

            # Phát âm thanh cảnh báo ngắn nếu kích hoạt cảnh báo mới
            if alert_messages and (now - last_alert_time) >= ALERT_COOLDOWN_SECONDS:
                play_alert()
                last_alert_time = now

            cv2.imshow("He thong phat hien buon ngu, mat tap trung va dien thoai", frame)

            # Lắng nghe phím bấm thoát (Q)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                print("[INFO] Nguoi dung an 'Q' de thoat. Dang dung camera...")
                system_state = "SAVING_DATA"
                break

    # Main loop ends
    pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Nhan tin hieu ngat KeyboardInterrupt.")
    finally:
        print("\n[INFO] Giai phong camera va cua so hien thi...")
        if cap is not None:
            try:
                cap.release()
            except Exception as e:
                print(f"[ERROR] Loi giai phong camera: {e}")
        cv2.destroyAllWindows()
        main_gpio_alert.cleanup()  # Giai phong GPIO (LED vang + buzzer)

        # Gửi dữ liệu cuối cùng lên Blynk trước khi thoát
        if blynk_enabled and blynk is not None:
            send_data_to_blynk(blynk, blynk_enabled, status)
        else:
            print("[BLYNK] Khong gui vi Blynk chua duoc cau hinh.")

        print("[INFO] Da thoat he thong hoan toan.")
