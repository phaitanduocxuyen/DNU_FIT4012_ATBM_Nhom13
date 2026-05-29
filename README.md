# Bài Tập Lớn: CF11 - Broken Authentication (Xác Thực Bị Lỗi)
**Môn học:** FIT4012 Cyber Fortress  
**Sinh viên thực hiện:** Phạm Anh Tú  
**Lớp:** CNTT 18 - 02  

---

## 1. Giới thiệu đề tài
Dự án giả lập một Hệ thống Quản lý Bài tập cục bộ (Local App) nhằm minh họa lỗ hổng **Broken Authentication** thuộc danh mục OWASP Top 10, cụ thể bao gồm hai lỗi logic phổ biến:
- Không giới hạn số lần đăng nhập sai (Thiếu Rate Limiting/Lockout) dẫn đến nguy cơ bị tấn công Brute-force đoán mật khẩu.
- Đăng xuất không hủy phiên (Session) trên Server, cho phép kẻ tấn công tái sử dụng Session token để truy cập trái phép.

## 2. Công cụ sử dụng
- Ngôn ngữ: Python 3
- Framework: Flask (Backend & Session Management)
- Giao diện: Bootstrap 5 (Responsive UI)

## 3. Cấu trúc thư mục nộp bài
```text
CF11-Broken-Authentication/
├── README.md
├── threat-model.md
├── ethics-safe-use.md
├── slides/
│   └── cyber-fortress-slides.pdf
├── demo/
│   └── app.py
└── evidence/
    ├── before.png
    ├── after.png
    └── logs.txt