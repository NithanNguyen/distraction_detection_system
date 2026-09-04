# Distraction Detection System

**Real-time attention, drowsiness and phone-usage monitoring for online learning and desk work — running fully on-device on a Raspberry Pi 4.**

![Python](https://img.shields.io/badge/Python-3.11.9-blue)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%204%20(aarch64)-c51a4a)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.18-orange)
![ONNX Runtime](https://img.shields.io/badge/ONNX%20Runtime-1.26.0-lightgrey)
![OpenCV](https://img.shields.io/badge/OpenCV-4.11.0-5c3ee8)
![License](https://img.shields.io/badge/License-<LICENSE>-green)

---

## Demo

<!-- Replace with a GIF/screenshot showing the live overlay (EAR / MAR / Yaw / status). -->
![Live overlay](docs/assets/demo.gif)

📹 **[Full demo video](<DEMO_VIDEO_URL>)**

---

## Abstract

Sustained attention is hard to measure objectively: time spent at a desk is a poor proxy for time
actually spent focused. Existing solutions rely on phone apps or wearables, which are either
self-reported or intrusive.

This project implements a **vision-based attention monitor on an embedded platform**. A USB webcam
feeds a MediaPipe Face Mesh pipeline that extracts 468 facial landmarks; from these the system derives
the Eye Aspect Ratio (EAR), Mouth Aspect Ratio (MAR) and head-pose Euler angles, and combines them with
a YOLO11n object detector to recognise five behavioural states. All inference runs **at the edge** — no
video frame ever leaves the device — and only aggregated counters are pushed to the cloud dashboard.

Evaluated on **88 functional test cases across 6 categories, the system reaches an 80 % pass rate
(70/88)**.

---

## Features

- **Drowsiness detection** — prolonged eye closure (EAR), yawning (MAR) and head drop (pitch).
- **Distraction detection** — gaze-away estimation from head-pose Euler angles (yaw / pitch).
- **Phone-usage detection** — YOLO11n running on ONNX Runtime (CPU-only, no PyTorch on the Pi).
- **Presence monitoring** — user absent from frame, or only partially inside the frame.
- **Environment guard** — low-light detection suppresses alerts when the scene is unreliable.
- **Local two-phase alerting** — yellow LED and active buzzer driven over GPIO.
- **Cloud telemetry** — state and per-behaviour counters pushed to a Blynk IoT dashboard.
- **Standalone appliance operation** — a button-driven supervisor process starts/stops the pipeline;
  no keyboard or SSH session required.

---

## System Architecture

![System architecture](docs/assets/architecture.png)
<img width="1360" height="880" alt="system_architecture" src="https://github.com/user-attachments/assets/04d6e568-e579-4e8f-94a5-56e51fb0f51a" />
<svg xmlns="http://www.w3.org/2000/svg" width="1360" height="880" viewBox="0 0 1360 880" font-family="Inter, 'Helvetica Neue', Arial, sans-serif" xmlns:c2pa="http://c2pa.org/manifest"><metadata><c2pa:manifest>AAAWgmp1bWIAAAAeanVtZGMycGEAEQAQgAAAqgA4m3EDYzJwYQAAABZcanVtYgAAAEdqdW1kYzJtYQARABCAAACqADibcQN1cm46YzJwYToxODJhNWQwOC1kZWZlLTQ1ZjMtYmU1ZS03ZDkwZjU0YzE1YzAAAAADl2p1bWIAAAApanVtZGMyYXMAEQAQgAAAqgA4m3EDYzJwYS5hc3NlcnRpb25zAAAAALxqdW1iAAAARGp1bWRjYm9yABEAEIAAAKoAOJtxE2MycGEuaW5ncmVkaWVudC52MwAAAAAYYzJzaP1aUjaYoTBPLERVcCADCFcAAABwY2JvcqNpZGM6Zm9ybWF0bWltYWdlL3N2Zyt4bWxqaW5zdGFuY2VJRHgseG1wOmlpZDo3MjJmZGYxNS0xZDJhLTQ0ZjQtODc5YS05MjhkMzIxM2UxMzZscmVsYXRpb25zaGlwaHBhcmVudE9mAAAB4mp1bWIAAABBanVtZGNib3IAEQAQgAAAqgA4m3ETYzJwYS5hY3Rpb25zLnYyAAAAABhjMnNoZNND0Xq9s3w7wH0fLMg8CwAAAZljYm9yomdhY3Rpb25zgqJmYWN0aW9ua2MycGEub3BlbmVkanBhcmFtZXRlcnOha2luZ3JlZGllbnRzgaJjdXJseC1zZWxmI2p1bWJmPWMycGEuYXNzZXJ0aW9ucy9jMnBhLmluZ3JlZGllbnQudjNkaGFzaFggAVABVhQhA0uKt/aZ084N6Gf3rRGtVRG6d3mCrcTOeu6kZmFjdGlvbngdY29tLmFudGhyb3BpYy5jbGF1ZGUucHJvdmlkZWRqcGFyYW1ldGVyc6F4H2NvbS5hbnRocm9waWMub3JpZ2luLWNvbmZpZGVuY2VndW5rbm93bmtkZXNjcmlwdGlvbnhmQ2xhdWRlIHByb3ZpZGVkIHRoaXMgZmlsZSBhdCB0aGUgcmVxdWVzdCBvZiBhIHVzZXIgYW5kIG1heSBoYXZlIGNyZWF0ZWQgb3IgbW9kaWZpZWQgdGhlIGZpbGUgY29udGVudHMubXNvZnR3YXJlQWdlbnShZG5hbWVmQ2xhdWRlcmFsbEFjdGlvbnNJbmNsdWRlZPUAAADIanVtYgAAAEBqdW1kY2JvcgARABCAAACqADibcRNjMnBhLmhhc2guZGF0YQAAAAAYYzJzaI3NUBFvElVkh6sLQLitEioAAACAY2JvcqVjYWxnZnNoYTI1NmNwYWRNAAAAAAAAAAAAAAAAAGRoYXNoWCBqZk1jOTfVmvwXhZMegELj65AuanfA44xD1aDOqXv3nmRuYW1lbmp1bWJmIG1hbmlmZXN0amV4Y2x1c2lvbnOBomVzdGFydBjRZmxlbmd0aBkeBAAAAj5qdW1iAAAAJ2p1bWRjMmNsABEAEIAAAKoAOJtxA2MycGEuY2xhaW0udjIAAAACD2Nib3KlY2FsZ2ZzaGEyNTZpc2lnbmF0dXJleE1zZWxmI2p1bWJmPS9jMnBhL3VybjpjMnBhOjE4MmE1ZDA4LWRlZmUtNDVmMy1iZTVlLTdkOTBmNTRjMTVjMC9jMnBhLnNpZ25hdHVyZWppbnN0YW5jZUlEeCx4bXA6aWlkOjRjNTMxZjVhLWMzMzEtNDUzZi1hNmNkLTY2MmRkOGZhNTZiNHJjcmVhdGVkX2Fzc2VydGlvbnODomN1cmx4LXNlbGYjanVtYmY9YzJwYS5hc3NlcnRpb25zL2MycGEuaW5ncmVkaWVudC52M2RoYXNoWCABUAFWFCEDS4q39pnTzg3oZ/etEa1VEbp3eYKtxM567qJjdXJseCpzZWxmI2p1bWJmPWMycGEuYXNzZXJ0aW9ucy9jMnBhLmFjdGlvbnMudjJkaGFzaFggTlfXND6fWfk/6nE3tydbgkCBx/IrGLetO2SnLl4HmlWiY3VybHgpc2VsZiNqdW1iZj1jMnBhLmFzc2VydGlvbnMvYzJwYS5oYXNoLmRhdGFkaGFzaFggwgH/eCeKvXmjakiZmCAWKcND3CabINxx2ifz8aZ0owB0Y2xhaW1fZ2VuZXJhdG9yX2luZm+jZG5hbWVvQW50aHJvcGljIEZpbGVzZ3ZlcnNpb25lMS4wLjBrc3BlY1ZlcnNpb25lMi40LjAAABA4anVtYgAAAChqdW1kYzJjcwARABCAAACqADibcQNjMnBhLnNpZ25hdHVyZQAAABAIY2JvctKEWQISogEmGCFZAgowggIGMIIBjaADAgECAhRA5aAK7sI50L64g/oGQgU9Z1UTADAKBggqhkjOPQQDAzBJMRcwFQYDVQQKEw5BbnRocm9waWMsIFBCQzEuMCwGA1UEAxMlQW50aHJvcGljIENvbnRlbnQgQ3JlZGVudGlhbHMgUm9vdCBDQTAeFw0yNjA4MDcxODQzNTZaFw0yODA4MDYxOTQzNTZaMEQxFzAVBgNVBAoTDkFudGhyb3BpYywgUEJDMSkwJwYDVQQDEyBBbnRocm9waWMgQ2xhdWRlIENvbnRlbnQgU2lnbmluZzBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABJh6CmvLUBgFFNU0vUKlOVtE6djd17L5SuwX0LemFisBM3dkd/3cyjxFA3Qo5S46fX0/ihY0VZ7mfb9KF703t5OjWDBWMA4GA1UdDwEB/wQEAwIHgDAVBgNVHSUEDjAMBgorBgEEAYPoXgIBMAwGA1UdEwEB/wQCMAAwHwYDVR0jBBgwFoAUzlHiBIFOZFsj+OPEz5o+nMHXXMIwCgYIKoZIzj0EAwMDZwAwZAIwMXMdFJ4BetLLVY7ORuE9noqbbAZOZn/aArXyTwFAZfKrPzxF2vPoJNf1+UCdg1XGAjBwX1zd9WGqYkqmL5SFqw1QySjr1zJfpJM9+1rdDwSPLMOPOjKuiXjoU/pUUeG9RwmhY3BhZFkNngAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPZYQAcbXNNgF29QPzxGb3FUfTgxy6LWTpDROZ4jt2Ep6H9eVaMdjK/6APnWAMkIMCWu0cBi6gnHw53u2Rh59bOv+n4=</c2pa:manifest></metadata>
  <defs>
    <marker id="aBlue" markerWidth="9" markerHeight="9" refX="7.5" refY="3.2" orient="auto">
      <path d="M0,0 L7.5,3.2 L0,6.4 z" fill="#3D6FA8"/>
    </marker>
    <marker id="aRed" markerWidth="9" markerHeight="9" refX="7.5" refY="3.2" orient="auto">
      <path d="M0,0 L7.5,3.2 L0,6.4 z" fill="#B5544F"/>
    </marker>
    <marker id="aGreen" markerWidth="9" markerHeight="9" refX="7.5" refY="3.2" orient="auto">
      <path d="M0,0 L7.5,3.2 L0,6.4 z" fill="#4A8352"/>
    </marker>
    <marker id="aPurple" markerWidth="9" markerHeight="9" refX="7.5" refY="3.2" orient="auto">
      <path d="M0,0 L7.5,3.2 L0,6.4 z" fill="#7E63A0"/>
    </marker>
  </defs>

  <rect width="1360" height="880" fill="#FFFFFF"/>

  <text x="680" y="48" text-anchor="middle" font-size="21" font-weight="700" fill="#12293F" letter-spacing="0.4">KIẾN TRÚC HỆ THỐNG</text>
  <text x="680" y="72" text-anchor="middle" font-size="12.5" fill="#6B7885">Giám sát mức độ tập trung bằng thị giác máy tính trên thiết bị nhúng</text>

  <text x="166" y="151" text-anchor="end" font-size="10.5" font-weight="700" fill="#9AA4AE" letter-spacing="0.8">NGOẠI VI VÀO</text>
  <text x="166" y="371" text-anchor="end" font-size="10.5" font-weight="700" fill="#9AA4AE" letter-spacing="0.8">THIẾT BỊ BIÊN</text>
  <text x="166" y="671" text-anchor="end" font-size="10.5" font-weight="700" fill="#9AA4AE" letter-spacing="0.8">NGOẠI VI RA</text>
  <text x="166" y="801" text-anchor="end" font-size="10.5" font-weight="700" fill="#9AA4AE" letter-spacing="0.8">DỊCH VỤ NGOÀI</text>

  <rect x="180" y="250" width="1080" height="310" rx="14" fill="#FDFBF4" stroke="#D9C48A" stroke-width="1.6"/>
  <text x="204" y="281" font-size="14" font-weight="700" fill="#8A6D1F">Raspberry Pi 4</text>

  <rect x="260" y="110" width="200" height="70" rx="9" fill="#EAF1FA" stroke="#7FA3CC" stroke-width="1.4"/>
  <text x="360" y="151" text-anchor="middle" font-size="14.5" fill="#1E3A57">Nút START / STOP</text>

  <rect x="600" y="110" width="200" height="70" rx="9" fill="#EAF1FA" stroke="#7FA3CC" stroke-width="1.4"/>
  <text x="700" y="151" text-anchor="middle" font-size="14.5" fill="#1E3A57">Webcam</text>

  <rect x="220" y="310" width="280" height="110" rx="10" fill="#FFFFFF" stroke="#E0A044" stroke-width="1.5"/>
  <text x="360" y="360" text-anchor="middle" font-size="15" font-weight="600" fill="#1F2933">pi_controller.py</text>
  <text x="360" y="382" text-anchor="middle" font-size="11.5" fill="#8A94A0">quản lý vòng đời</text>

  <rect x="560" y="310" width="280" height="110" rx="10" fill="#FFFFFF" stroke="#E0A044" stroke-width="1.5"/>
  <text x="700" y="360" text-anchor="middle" font-size="15" font-weight="600" fill="#1F2933">main.py</text>
  <text x="700" y="382" text-anchor="middle" font-size="11.5" fill="#8A94A0">pipeline thị giác máy tính</text>

  <rect x="900" y="310" width="280" height="110" rx="10" fill="#FFFFFF" stroke="#E0A044" stroke-width="1.5"/>
  <text x="1040" y="360" text-anchor="middle" font-size="15" font-weight="600" fill="#1F2933">main_gpio_alert.py</text>
  <text x="1040" y="382" text-anchor="middle" font-size="11.5" fill="#8A94A0">driver cảnh báo</text>

  <rect x="380" y="450" width="160" height="56" rx="8" fill="#F4F5F6" stroke="#B4BCC4" stroke-width="1.3"/>
  <text x="460" y="483" text-anchor="middle" font-size="13" fill="#4B5661">microSD</text>

  <rect x="750" y="450" width="160" height="56" rx="8" fill="#F4F5F6" stroke="#B4BCC4" stroke-width="1.3"/>
  <text x="830" y="483" text-anchor="middle" font-size="13" fill="#4B5661">Wi-Fi</text>

  <rect x="260" y="630" width="200" height="70" rx="9" fill="#E9F3E9" stroke="#7FB183" stroke-width="1.4"/>
  <text x="360" y="671" text-anchor="middle" font-size="14.5" fill="#1F3D23">LED xanh</text>

  <rect x="600" y="630" width="200" height="70" rx="9" fill="#E9F3E9" stroke="#7FB183" stroke-width="1.4"/>
  <text x="700" y="671" text-anchor="middle" font-size="14.5" fill="#1F3D23">Màn hình HDMI</text>

  <rect x="860" y="630" width="190" height="70" rx="9" fill="#E9F3E9" stroke="#7FB183" stroke-width="1.4"/>
  <text x="955" y="671" text-anchor="middle" font-size="14.5" fill="#1F3D23">LED vàng</text>

  <rect x="1070" y="630" width="190" height="70" rx="9" fill="#E9F3E9" stroke="#7FB183" stroke-width="1.4"/>
  <text x="1165" y="671" text-anchor="middle" font-size="14.5" fill="#1F3D23">Buzzer</text>

  <rect x="900" y="760" width="190" height="70" rx="9" fill="#F1EBF6" stroke="#A98FC4" stroke-width="1.4"/>
  <text x="995" y="801" text-anchor="middle" font-size="14.5" fill="#3D2C50">Blynk Cloud</text>

  <rect x="1130" y="760" width="190" height="70" rx="9" fill="#F1EBF6" stroke="#A98FC4" stroke-width="1.4"/>
  <text x="1225" y="801" text-anchor="middle" font-size="14.5" fill="#3D2C50">Blynk App</text>

  <line x1="360" y1="180" x2="360" y2="304" stroke="#3D6FA8" stroke-width="1.7" marker-end="url(#aBlue)"/>
  <rect x="366" y="234" width="58" height="17" fill="#FFFFFF"/>
  <text x="370" y="247" font-size="11" fill="#3D6FA8">GPIO26</text>

  <line x1="700" y1="180" x2="700" y2="304" stroke="#3D6FA8" stroke-width="1.7" marker-end="url(#aBlue)"/>
  <rect x="706" y="234" width="34" height="17" fill="#FFFFFF"/>
  <text x="710" y="247" font-size="11" fill="#3D6FA8">USB</text>

  <line x1="500" y1="365" x2="554" y2="365" stroke="#B5544F" stroke-width="1.7" marker-end="url(#aRed)"/>
  <text x="527" y="303" text-anchor="middle" font-size="11" fill="#B5544F">spawn / SIGTERM</text>

  <line x1="840" y1="365" x2="894" y2="365" stroke="#B5544F" stroke-width="1.7" marker-end="url(#aRed)"/>
  <text x="867" y="303" text-anchor="middle" font-size="11" fill="#B5544F">update()</text>

  <line x1="360" y1="420" x2="360" y2="624" stroke="#4A8352" stroke-width="1.7" marker-end="url(#aGreen)"/>
  <rect x="366" y="586" width="58" height="17" fill="#FFFFFF"/>
  <text x="370" y="599" font-size="11" fill="#4A8352">GPIO22</text>

  <line x1="700" y1="420" x2="700" y2="624" stroke="#4A8352" stroke-width="1.7" marker-end="url(#aGreen)"/>
  <rect x="706" y="586" width="42" height="17" fill="#FFFFFF"/>
  <text x="710" y="599" font-size="11" fill="#4A8352">HDMI</text>

  <line x1="955" y1="420" x2="955" y2="624" stroke="#4A8352" stroke-width="1.7" marker-end="url(#aGreen)"/>
  <rect x="961" y="586" width="58" height="17" fill="#FFFFFF"/>
  <text x="965" y="599" font-size="11" fill="#4A8352">GPIO17</text>

  <line x1="1165" y1="420" x2="1165" y2="624" stroke="#4A8352" stroke-width="1.7" marker-end="url(#aGreen)"/>
  <rect x="1171" y="586" width="58" height="17" fill="#FFFFFF"/>
  <text x="1175" y="599" font-size="11" fill="#4A8352">GPIO27</text>

  <line x1="830" y1="420" x2="830" y2="444" stroke="#7E63A0" stroke-width="1.7" stroke-dasharray="6 4" marker-end="url(#aPurple)"/>
  <path d="M830,506 L830,795 L894,795" fill="none" stroke="#7E63A0" stroke-width="1.7" stroke-dasharray="6 4" marker-end="url(#aPurple)"/>
  <rect x="838" y="726" width="76" height="17" fill="#FFFFFF"/>
  <text x="842" y="739" font-size="11" fill="#7E63A0">HTTPS REST</text>

  <line x1="1090" y1="795" x2="1124" y2="795" stroke="#7E63A0" stroke-width="1.7" stroke-dasharray="6 4" marker-end="url(#aPurple)"/>

  <line x1="200" y1="856" x2="232" y2="856" stroke="#3D6FA8" stroke-width="1.8"/>
  <text x="240" y="860" font-size="11.5" fill="#6B7885">dữ liệu vào</text>

  <line x1="335" y1="856" x2="367" y2="856" stroke="#B5544F" stroke-width="1.8"/>
  <text x="375" y="860" font-size="11.5" fill="#6B7885">điều khiển tiến trình</text>

  <line x1="520" y1="856" x2="552" y2="856" stroke="#4A8352" stroke-width="1.8"/>
  <text x="560" y="860" font-size="11.5" fill="#6B7885">điều khiển ngoại vi</text>

  <line x1="695" y1="856" x2="727" y2="856" stroke="#7E63A0" stroke-width="1.8" stroke-dasharray="6 4"/>
  <text x="735" y="860" font-size="11.5" fill="#6B7885">mạng Internet</text>
</svg>



### Processing pipeline

```
USB webcam
   └─▶ OpenCV capture & preprocessing
         └─▶ MediaPipe Face Mesh — 468 landmarks
               ├─▶ EAR / MAR                  (eye & mouth aperture)
               ├─▶ solvePnP → yaw/pitch/roll  (head pose)
               └─▶ YOLO11n (ONNX)             (phone detection, every 4th frame)
                     └─▶ Threshold + dwell-time state machine
                           ├─▶ GPIO alert (yellow LED + buzzer)
                           ├─▶ HDMI overlay (cv2.imshow)
                           └─▶ Blynk HTTP API (V0 state, V1–V5 counters)
```

### Process model

The system runs as **two cooperating processes** on two different Python interpreters, because the CV
stack and the GPIO stack have incompatible runtime requirements on Debian 13:

| Process | Interpreter | Owns | Role |
|---|---|---|---|
| `pi_controller.py` | system Python 3.13 (`apt` gpiozero/lgpio) | GPIO22 (green LED), GPIO26 (button) | Supervisor. `IDLE`: green LED blinks at 1 Hz. Button press spawns `main.py` → `RUNNING`. Second press sends `SIGTERM`, waits up to 8 s for cleanup, then `SIGKILL`. Auto-reaps a crashed child. |
| `main.py` | venv Python 3.11.9 (MediaPipe, ONNX Runtime, OpenCV) | GPIO17 (yellow LED), GPIO27 (buzzer) via `main_gpio_alert` | Vision pipeline, state machine, alerting, telemetry. Handles `SIGTERM` by releasing GPIO and the camera. |

The supervisor is started at login by a systemd **user** unit (`pi-controller.service`).

---

## Methodology

### Detection criteria

Every behavioural state requires the metric to stay past its threshold for a minimum **dwell time**,
which suppresses false positives from natural blinks and brief head movements.

| Metric | Quantity | Threshold | Dwell time | Inferred state |
|---|---|---|---|---|
| EAR | eye aspect ratio | `< 0.20` | 1.3 s | Eyes closed / drowsy |
| MAR | mouth aspect ratio | `> 0.50` | 1.0 s | Yawning |
| Yaw / Pitch | Euler angles, relative to calibrated baseline | enter `20°` / exit `15°` (yaw), enter `20°` / exit `12°` (pitch) | 4.5 s | Gaze away — distracted |
| Pitch | relative head drop | `> 28°` | 1.0 s | Head down (pick-up object / drowsy) |
| YOLO11n | phone class confidence | `≥ 0.45` | 1.5 s | Phone usage |
| Face Mesh | no face detected | — | 2.0 s | User absent |
| Face bbox | face partially outside frame (25 px margin) | — | 1.0 s | Invalid presence |
| Frame stats | mean brightness `< 60`, noise `< 15` | — | 1.5 s | Low light — monitoring suspended |

### Signal-processing safeguards

Raw `solvePnP` output on a 30 fps embedded stream is noisy; three mechanisms stabilise it:

1. **Per-user pose calibration** — the first 2 s (≥ 15 samples) are reduced by a median to a personal
   baseline `(pitch₀, yaw₀, roll₀)`. All later angles are expressed relative to it, so a naturally
   tilted sitting posture is not misread as distraction.
2. **Exponential moving average** (`α = 0.25`) plus a **20°/frame jump clamp**, rejecting PnP solution
   flips and single-frame landmark outliers.
3. **Hysteresis** on the distraction thresholds (enter 20°, exit 15°) to prevent state chattering when
   the head hovers near the boundary. Faces smaller than 120 px are excluded from pose estimation.

### Alert pattern

Escalating feedback, driven every frame by `main_gpio_alert.update(alert_active)`:

| Elapsed since alert | Yellow LED | Buzzer |
|---|---|---|
| 0 – 2 s | blink, 0.5 s period (0.25 on / 0.25 off) | off |
| > 2 s | blink, 1 s period (0.5 on / 0.5 off) | synchronous with LED |
| alert cleared | off immediately, timer reset | off |

---

## Results

88 valid test cases across six functional groups:

| Group | Function | Cases | Pass | Fail | Pass rate |
|---|---|---:|---:|---:|---:|
| A | Presence in frame | 18 | 13 | 5 | 72 % |
| B | Gaze direction & focus | 12 | 12 | 0 | 100 % |
| C | Phone usage | 20 | 17 | 3 | 85 % |
| D | Drowsiness & fatigue | 13 | 9 | 4 | 69 % |
| E | Abnormal behaviour | 15 | 9 | 6 | 60 % |
| F | Environment & fault handling | 10 | 10 | 0 | 100 % |
| **Total** | | **88** | **70** | **18** | **80 %** |

**Strengths.** Head-pose based gaze estimation and environmental fault handling were fully reliable
(groups B and F). Clearly expressed behaviours — long eye closure, head slump, leaving the desk — are
detected consistently. All recognition happens on-device, so no image data is transmitted.

**Known limitations.**
- The fixed EAR threshold under-detects subtle drowsiness and cannot distinguish rapid natural blinking
  from fatigue (group D failures).
- Brief glances at a phone that involve eye movement without head rotation are missed (group C).
- The pipeline tracks a **single user**; multi-person frames are unsupported (group E).
- The temporal boundary between "briefly leaving the seat" and "genuinely absent" is not yet
  well-separated (group A).

---

## Hardware

| Component | Specification |
|---|---|
| SBC | Raspberry Pi 4 Model B |
| OS | Debian GNU/Linux 13 (trixie), kernel 6.12, aarch64 |
| Camera | USB webcam (`CAMERA_INDEX = 0`) |
| Display | HDMI monitor (live overlay window) |
| Indicators | 2 × LED (green, yellow) + 330 Ω series resistors |
| Alert | Active buzzer (< 25 mA — connect directly; otherwise drive via transistor) |
| Input | Momentary push button (internal pull-up, active LOW) |

### GPIO map

| BCM | Header pin | Device | Direction |
|---|---|---|---|
| GPIO22 | 15 | Green LED (system state) | out |
| GPIO26 | 37 | Button | in, pull-up |
| GPIO17 | 11 | Yellow LED (alert) | out |
| GPIO27 | 13 | Active buzzer | out |

Full wiring diagram: [`docs/DEPLOY.md`](docs/DEPLOY.md).

---

## Quick Start

> Assumes Python 3.11.9 is already available through `pyenv` on the Pi.
> First-time setup on a clean device is **not** trivial — follow
> [`docs/INSTALL.md`](docs/INSTALL.md).

```bash
git clone https://github.com/<OWNER>/distraction_detection_system.git
cd distraction_detection_system

python3 -m venv venv --system-site-packages && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # set BLYNK_AUTH_TOKEN
# place yolo11n.onnx in the project root (see docs/INSTALL.md §Model preparation)

/usr/bin/python3 pi_controller.py   # supervisor — press the button to start
```

Run the vision pipeline directly, without the supervisor:

```bash
source venv/bin/activate && python3 main.py
```

---

## Repository Structure

```
.
├── main.py                 # Vision pipeline, state machine, Blynk telemetry
├── main_gpio_alert.py      # Yellow LED + buzzer driver (two-phase alert pattern)
├── pi_controller.py        # Supervisor: green LED, button, main.py lifecycle
├── pi-controller.service   # systemd user unit (autostart on login)
├── requirements.txt
├── .env.example
└── docs/
    ├── INSTALL.md          # Full setup on Pi 4 + ONNX model export
    ├── DEPLOY.md           # Wiring, GPIO, systemd deployment
    ├── TROUBLESHOOTING.md  # Known build/runtime failures and fixes
    └── assets/
```

---

## Configuration

All tuning parameters live in a single block at the top of `main.py`. The three most commonly adjusted:

| Constant | Default | Effect |
|---|---|---|
| `EAR_THRESHOLD` | `0.20` | Lower ⇒ fewer drowsiness alerts. Person-dependent; tune per user. |
| `DISTRACT_SECONDS` | `4.5` | Dwell time before a gaze deviation is reported. |
| `USE_PHONE_DETECTION` | `True` | Set `False` to skip YOLO inference and reclaim CPU headroom. |

Blynk virtual pins: `V0` = current state (string), `V1` drowsiness, `V2` gaze deviation, `V3` absence,
`V4` phone usage, `V5` abnormal behaviour. Counters are pushed on change and re-synced every 60 s.

> **Security.** `BLYNK_AUTH_TOKEN` must be supplied through the environment (`.env`), never committed.

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/INSTALL.md`](docs/INSTALL.md) | Environment matrix, pyenv 3.11.9, MediaPipe aarch64 wheel, YOLO → ONNX export |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | Wiring diagram, GPIO libraries, systemd user service |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | 8 documented build/runtime failures (MediaPipe wheels, NumPy ABI conflicts, `Illegal instruction` on Cortex-A72, Qt/Wayland warnings) and their fixes |

---

## Roadmap

- Adaptive, per-user EAR thresholding to replace the fixed cutoff.
- Multi-person tracking with per-subject state machines.
- INT8 quantisation of the ONNX detector to raise sustained frame rate on the Pi 4.

---

## References

1. Kaewkaisorn et al. *Student attentiveness analysis in virtual classroom using distraction, drowsiness and emotion detection.* Discover Education (2024). https://doi.org/10.1007/s44217-024-00117-7
2. Buono et al. *Assessing student engagement from facial behavior in on-line learning.* Multimedia Tools and Applications (2023). https://doi.org/10.1007/s11042-022-14048-8
3. *A multimodal facial cues based engagement detection system in e-learning context using deep learning approach.* Multimedia Tools and Applications (2023). https://doi.org/10.1007/s11042-023-14392-3
4. *Real-Time Student Engagement Monitoring via Facial Landmark Analysis.* IJMECS 18(1). https://www.mecs-press.org/ijmecs/ijmecs-v18-n1/v18n1-5.html
5. *Student Engagement Detection Based on Head Pose Estimation and Facial Expressions Using Transfer Learning.* Springer (2025). https://doi.org/10.1007/978-3-031-88653-9_25
6. Khan, R. & Debnath, R. *Human distraction detection from video stream using artificial emotional intelligence.* Int. J. Image, Graphics and Signal Processing 12(2), 19–29 (2020).

---

## Team

**CE Comedians** — Course CE410 — Computer Systems Engineering. 
Faculty of Computer Engineering, University of Information Technology, VNU-HCM.

## License

<LICENSE — e.g. MIT>
