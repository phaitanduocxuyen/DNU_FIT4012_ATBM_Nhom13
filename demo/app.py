from flask import Flask, request, render_template_string, redirect, url_for, make_response, session
import sqlite3
import time
import secrets
import re
import os

app = Flask(__name__)
# Cấu hình Secret Key để sử dụng bộ nhớ session tạm thời của Flask cho bước MFA
app.secret_key = secrets.token_hex(16)

# Cấu hình chế độ mặc định: False = Bản lỗi Broken Auth, True = Bản vá bảo mật
SECURITY_MODE = False

# Lưu trữ danh sách Session đang hoạt động trên Server (In-memory Session Storage)
# Cấu trúc: { "token_id": {"username": "...", "last_activity": timestamp} }
SERVER_SESSIONS = {}

DB_FILE = 'cyber_fortress.db'

def init_db_if_not_exists():
    """Hàm tự động khởi tạo cơ sở dữ liệu SQLite"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            failed_attempts INTEGER DEFAULT 0,
            lockout_until REAL DEFAULT 0
        )
    ''')
    try:
        # THIẾT LẬP TÀI KHOẢN ĐỂ DEMO ĐỐI CHỨNG THEO SLIDE
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', 'Admin@1234')) # Mật khẩu MẠNH
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('student', '123456'))    # Mật khẩu YẾU
        conn.commit()
        print("[+] Tự động khởi tạo dữ liệu tài khoản thành công!")
    except sqlite3.IntegrityError:
        pass
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def is_strong_password(password):
    """Hàm kiểm tra tiêu chuẩn mật khẩu mạnh (Password Policy)"""
    if len(password) < 8:
        return False
    if not re.search("[a-z]", password) or not re.search("[A-Z]", password) or not re.search("[0-9]", password):
        return False
    if not re.search("[_@$!%*?&]", password):
        return False
    return True

# --- GIAO DIỆN TÍCH HỢP BOOTSTRAP 5 CHUYÊN NGHIỆP ---
HTML_HEADER = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FIT4012 - Cyber Fortress CF11</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #f4f6f9; min-height: 100vh; display: flex; align-items: center; justify-content: center; flex-direction: column; }
        .card-custom { width: 100%; max-width: 440px; border: none; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.07); }
    </style>
</head>
<body>
"""
HTML_FOOTER = "</body></html>"

LOGIN_PAGE = HTML_HEADER + """
<div class="card card-custom">
    <div class="card-header bg-dark text-white text-center py-3">
        <h5 class="mb-0">HỆ THỐNG QUẢN LÝ BÀI TẬP</h5>
        <small class="text-muted">Cyber Fortress Lab - Broken Authentication</small>
    </div>
    <div class="card-body p-4">
        {% if mode %}
            <div class="alert alert-success text-center fw-bold py-2">🛡️ CHẾ ĐỘ: ĐÃ VÁ (SECURED)</div>
        {% else %}
            <div class="alert alert-danger text-center fw-bold py-2">⚠️ CHẾ ĐỘ: BẢN LỖI (VULNERABLE)</div>
        {% endif %}

        {% if lockout_seconds %}
            <div class="alert alert-danger text-center fw-bold py-3 border border-danger shadow-sm">
                🚨 TÀI KHOẢN BỊ KHÓA TẠM THỜI<br>
                <span class="fs-4 text-dark" id="countdown-timer">{{ lockout_seconds }}</span> giây còn lại...
            </div>
            <script>
                let timeRemaining = {{ lockout_seconds }};
                const timerDisplay = document.getElementById('countdown-timer');
                const countdownInterval = setInterval(() => {
                    timeRemaining--;
                    if (timeRemaining <= 0) {
                        clearInterval(countdownInterval);
                        window.location.href = "/";
                    } else {
                        timerDisplay.innerText = timeRemaining;
                    }
                }, 1000);
            </script>
        {% elif error %}
            <div class="alert alert-warning py-2 text-center small text-danger fw-bold">{{ error }}</div>
        {% endif %}

        <form method="POST" action="/login" {% if lockout_seconds %}style="opacity: 0.5; pointer-events: none;"{% endif %}>
            <div class="mb-3">
                <label class="form-label fw-medium">Tên tài khoản</label>
                <input type="text" name="username" class="form-control" required placeholder="admin / student" {% if lockout_seconds %}disabled{% endif %}>
            </div>
            <div class="mb-3">
                <label class="form-label fw-medium">Mật khẩu</label>
                <input type="password" name="password" class="form-control" required {% if lockout_seconds %}disabled{% endif %}>
            </div>

            {% if show_captcha and not lockout_seconds %}
            <div class="mb-3 p-3 bg-light rounded border border-warning">
                <label class="form-label fw-bold text-danger">🧠 CAPTCHA Tích phân chặn Bot:</label>
                <div class="mb-2 text-center bg-dark text-warning rounded py-2 font-monospace fs-5">
                    <b>I = &int;<sub>0</sub><sup>1</sup> [ x / (4 - x<sup>2</sup>) ] dx = ?</b>
                </div>
                <input type="text" name="captcha_ans" class="form-control text-center fw-bold" placeholder="Nhập giá trị thập phân (Làm tròn 2 số)" required>
                <div class="form-text text-center small text-muted">Đáp án tính toán thực tế: <b>0.14</b></div>
            </div>
            {% endif %}

            <button type="submit" class="btn btn-dark w-100 fw-bold py-2" {% if lockout_seconds %}disabled{% endif %}>ĐĂNG NHẬP</button>
        </form>
    </div>
    <div class="card-footer text-center py-2 bg-light" style="border-radius: 0 0 12px 12px;">
        <a href="/toggle-mode" class="btn btn-sm btn-outline-secondary w-100">Bấm Để Chuyển Chế Độ Demo</a>
    </div>
</div>
""" + HTML_FOOTER

MFA_PAGE = HTML_HEADER + """
<div class="card card-custom border-warning">
    <div class="card-header bg-warning text-dark text-center py-3">
        <h5 class="mb-0">🛡️ YÊU CẦU XÁC THỰC LỚP HAI (MFA / OTP)</h5>
        <small>Tài khoản xác minh thành công: <b class="text-danger">{{ username }}</b></small>
    </div>
    <div class="card-body p-4 text-center">
        <div class="alert alert-warning py-2 small">Hệ thống kích hoạt lớp bảo vệ OTP nâng cao chống chiếm quyền lợi.</div>
        {% if error %}<div class="alert alert-danger py-1 small fw-bold">{{ error }}</div>{% endif %}
        <form method="POST" action="/verify-mfa">
            <div class="mb-3">
                <input type="text" name="otp" class="form-control text-center fs-3 fw-bold" placeholder="******" required>
                <div class="form-text mt-2">Mã OTP thử nghiệm mặc định: <b>123456</b></div>
            </div>
            <button type="submit" class="btn btn-warning w-100 fw-bold text-dark py-2">XÁC NHẬN CODE OTP</button>
        </form>
    </div>
</div>
""" + HTML_FOOTER

DASHBOARD_PAGE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Hệ Thống Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<nav class="navbar navbar-expand-lg navbar-dark bg-dark shadow">
    <div class="container">
        <a class="navbar-brand fw-bold text-info" href="#">FIT4012 LAB</a>
        <span class="navbar-text text-white">Đang đăng nhập: <b class="text-warning">{{ username }}</b></span>
        <a href="/logout" class="btn btn-danger btn-sm fw-bold px-3">Đăng Xuất</a>
    </div>
</nav>

<div class="container mt-5">
    <div class="bg-white p-5 rounded shadow-sm border">
        <h2 class="fw-bold">Khu Vực Quản Lý Bài Tập Nhạy Cảm</h2>
        <p class="text-muted">Tài sản dữ liệu được bảo mật chống rò rỉ.</p>
        <hr>
        
        <div class="alert alert-info py-2">
            <b>⏱️ Cơ chế Session Timeout tự động:</b> 
            {% if secured %}
                <span class="text-success fw-bold">BẬT (Hết hạn sau 30 giây nhàn rỗi để Demo nhanh)</span>
            {% else %}
                <span class="text-danger fw-bold">TẮT (Phiên làm việc kéo dài vô hạn, nguy cơ Session Hijacking)</span>
            {% endif %}
        </div>

        <div class="card border-info bg-light-subtle mb-4">
            <div class="card-body">
                <h6 class="card-title fw-bold text-primary">Giá Trị Session Token thực tế trong Cookie:</h6>
                <code class="fs-5 bg-dark text-warning p-2 d-block rounded mt-2 text-center" id="token-text">{{ token_val }}</code>
            </div>
        </div>
        
        <a href="/" class="btn btn-primary btn-sm">F5 Tải lại trang (Kiểm thử Timeout)</a>
    </div>
</div>
</body>
</html>
"""

# --- LOGIC XỬ LÝ BACKEND SERVER ---

@app.route('/')
def index():
    session_token = request.cookies.get('session_token')
    if session_token and session_token in SERVER_SESSIONS:
        session_data = SERVER_SESSIONS[session_token]
        
        # KIỂM TRA ĐIỀU KIỆN TIMEOUT (Yêu cầu Sau Khi Vá)
        if SECURITY_MODE:
            if time.time() - session_data['last_activity'] > 30: # 30 giây nhàn rỗi
                del SERVER_SESSIONS[session_token]
                response = make_response(redirect(url_for('index')))
                response.delete_cookie('session_token')
                return response
            SERVER_SESSIONS[session_token]['last_activity'] = time.time() # Cập nhật tương tác
            
        return render_template_string(DASHBOARD_PAGE, username=session_data['username'], token_val=session_token, secured=SECURITY_MODE)
    return render_template_string(LOGIN_PAGE, mode=SECURITY_MODE, error=None, show_captcha=False, lockout_seconds=0)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username').strip()
    password = request.form.get('password').strip()
    captcha_ans = request.form.get('captcha_ans')
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    
    # 📌 TỰ ĐỘNG ĐỊNH VỊ ĐƯỜNG DẪN VÀ GHI LOG VÀO THƯ MỤC EVIDENCE/LOGS.TXT
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    evidence_dir = os.path.join(root_dir, 'evidence')
    if not os.path.exists(evidence_dir):
        os.makedirs(evidence_dir)
    log_file_path = os.path.join(evidence_dir, 'logs.txt')

    current_time = time.strftime('%Y-%m-%d %H:%M:%S')
    log_prefix = f"[{current_time}]"
    if user and user['failed_attempts'] >= 3 and SECURITY_MODE:
        log_prefix += " [🚨 CRITICAL WARNING - ANOMALY DETECTED]"

    log_msg = f"{log_prefix} Login Request | User: '{username}' | Mode: {'Secured' if SECURITY_MODE else 'Vulnerable'}\n"
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(log_msg)

    if not user:
        conn.close()
        return render_template_string(LOGIN_PAGE, mode=SECURITY_MODE, error="Tài khoản không tồn tại!", lockout_seconds=0)

    if SECURITY_MODE:
        # --- BẢN VÁ BẢO MẬT (SECURED) ---
        
        # 1. Kiểm tra trạng thái khóa tài khoản Lockout trước tiên
        if user['lockout_until'] > time.time():
            remaining_time = int(user['lockout_until'] - time.time())
            conn.close()
            return render_template_string(LOGIN_PAGE, mode=SECURITY_MODE, error=None, show_captcha=False, lockout_seconds=remaining_time)

        # 2. Kiểm tra xác minh CAPTCHA toán học tích phân nâng cao
        if user['failed_attempts'] >= 2:
            if not captcha_ans or captcha_ans.strip() != "0.14":
                conn.close()
                return render_template_string(LOGIN_PAGE, mode=SECURITY_MODE, error="Mã CAPTCHA sai! Tích phân chưa tính đúng.", show_captcha=True, lockout_seconds=0)

        # 3. Kiểm tra thông tin tài khoản
        if user['password'] == password:
            # CHẶN ĐĂNG NHẬP NẾU MẬT KHẨU ĐÚNG NHƯNG BỊ YẾU (Password Policy)
            if not is_strong_password(password):
                conn.close()
                return render_template_string(LOGIN_PAGE, mode=SECURITY_MODE, error="[🛡️ CHẶN TRUY CẬP] Bản vá kích hoạt Password Policy: Từ chối xử lý phiên cho tài khoản sử dụng mật khẩu yếu (như 123456)!", show_captcha=False, lockout_seconds=0)
            
            # Lưu tài khoản hợp lệ vào session tạm thời để phục vụ bước MFA/OTP tiếp theo
            session['mfa_user'] = username
            conn.execute('UPDATE users SET failed_attempts = 0, lockout_until = 0 WHERE username = ?', (username,))
            conn.commit()
            conn.close()
            return render_template_string(MFA_PAGE, username=username, error=None)
        else:
            # Nhập mật khẩu sai: Tăng bộ đếm lỗi liên tiếp
            new_attempts = user['failed_attempts'] + 1
            error_msg = f"Sai mật khẩu! Bạn còn {5 - new_attempts} lần thử."
            show_cap = True if new_attempts >= 2 else False
            lock_sec = 0
            
            if new_attempts >= 5:
                lockout_time = time.time() + 60 # Khóa đếm ngược 60 giây
                conn.execute('UPDATE users SET failed_attempts = ?, lockout_until = ? WHERE username = ?', (new_attempts, lockout_time, username))
                error_msg = None
                show_cap = False
                lock_sec = 60
            else:
                conn.execute('UPDATE users SET failed_attempts = ? WHERE username = ?', (new_attempts, username))
            
            conn.commit()
            conn.close()
            return render_template_string(LOGIN_PAGE, mode=SECURITY_MODE, error=error_msg, show_captcha=show_cap, lockout_seconds=lock_sec)
            
    else:
        # --- BẢN LỖI LOGIC (VULNERABLE) ---
        if user['password'] == password:
            conn.close()
            # Cấp trực tiếp mã token plaintext giả lập
            session_token = f"TOKEN_GIA_LAP_{username}_{secrets.token_hex(4)}"
            SERVER_SESSIONS[session_token] = {"username": username, "last_activity": time.time()}
            
            response = make_response(redirect(url_for('index')))
            response.set_cookie('session_token', session_token)
            return response
        else:
            conn.close()
            return render_template_string(LOGIN_PAGE, mode=SECURITY_MODE, error="Mật khẩu không hợp lệ! (Hệ thống không chặn giới hạn)", lockout_seconds=0)

@app.route('/verify-mfa', methods=['POST'])
def verify_mfa():
    otp = request.form.get('otp').strip()
    username = session.get('mfa_user', 'admin')
    
    if otp == "123456" and SECURITY_MODE:
        # Sinh Token độ hỗn loạn cao (High-Entropy Token) an toàn
        session_token = secrets.token_hex(32)
        SERVER_SESSIONS[session_token] = {"username": username, "last_activity": time.time()}
        
        response = make_response(redirect(url_for('index')))
        response.set_cookie('session_token', session_token, httponly=True)
        return response
    else:
        return render_template_string(MFA_PAGE, username=username, error="Mã OTP sai! Nhập mã mặc định: 123456")

@app.route('/logout')
def logout():
    response = make_response(redirect(url_for('index')))
    session_token = request.cookies.get('session_token')
    
    if SECURITY_MODE:
        # BẢN VÁ: Hủy triệt để cả hai đầu
        if session_token in SERVER_SESSIONS:
            del SERVER_SESSIONS[session_token]
        response.delete_cookie('session_token')
    else:
        # BẢN LỖI: Chỉ xóa cookie client, giữ nguyên session trên server để làm Replay Attack
        response.delete_cookie('session_token')
        
    return response

@app.route('/toggle-mode')
def toggle_mode():
    global SECURITY_MODE
    SECURITY_MODE = not SECURITY_MODE
    SERVER_SESSIONS.clear()
    response = make_response(redirect(url_for('index')))
    response.delete_cookie('session_token')
    return response

if __name__ == '__main__':
    # Tự động làm sạch database cũ khi bật lên để cập nhật mật khẩu đồng bộ
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    init_db_if_not_exists()
    app.run(debug=True, port=5000)