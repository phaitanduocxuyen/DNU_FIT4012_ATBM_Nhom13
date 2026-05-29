# Threat Model - Cyber Fortress (CF11 - Broken Authentication)

## 1. Asset - Tài sản cần bảo vệ
- Tài khoản người dùng (Quyền truy cập của giảng viên, sinh viên).
- Dữ liệu bài tập, điểm số lưu trữ trên hệ thống.
- Session token của người dùng đang hoạt động.

## 2. Threat - Mối đe dọa
- Kẻ tấn công bên ngoài thực hiện rò quét tự động (Automated Scripts).
- Botnet thực hiện Brute-force mật khẩu quy mô nhỏ dựa trên danh sách mật khẩu phổ biến.
- Người dùng chung máy tính công cộng cố tình truy cập lại lịch sử duyệt web để chiếm quyền điều khiển phiên (Session Reuse).

## 3. Vulnerability - Lỗ hổng
- Không có cơ chế Rate Limiting hoặc Lockout khi xảy ra đăng nhập sai liên tiếp.
- Cơ chế Đăng xuất (Logout) bị lỗi logic: Chỉ thực hiện điều hướng trang ở phía Client/Giao diện mà không tiến hành thu hồi, xóa bỏ giá trị Session Token tương ứng ở phía Server-side.

## 4. Impact - Tác động
- Kẻ tấn công có thể dò ra mật khẩu của tài khoản quản trị thông qua việc thử liên tục.
- Chiếm quyền điều khiển tài khoản (Account Takeover), dẫn đến rò rỉ dữ liệu điểm số hoặc sửa đổi bài tập.
- Mất tính bảo mật của toàn bộ phiên làm việc của người dùng sau khi họ tin rằng mình đã thoát ứng dụng thành công.

## 5. Mitigation - Biện pháp giảm thiểu
- Kỹ thuật: Triển khai bộ đếm lưu vào bộ nhớ tạm để khóa tài khoản tạm thời (Lockout) trong 5 phút nếu nhập sai quá 5 lần.
- Kỹ thuật: Ép buộc Server xóa bỏ hoàn toàn trạng thái Session của định danh phiên bằng các hàm xóa chuyên dụng (`session.clear()`) ngay khi nhận yêu cầu logout.
- Quy trình: Áp dụng quy chuẩn Password Policy (độ dài tối thiểu 8 ký tự, có ký tự đặc biệt) để giảm thiểu khả năng bị Brute-force thủ công.