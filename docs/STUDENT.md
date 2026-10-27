# Đề bài: Range Shop

Thời lượng dự kiến 30–45 phút; cần biết HTTP, cookie và SELECT/UNION cơ bản.

Bạn được cung cấp một cửa hàng demo ở `http://10.20.10.10:8080/` trong sandbox.
Giảng viên cung cấp đường truy cập/tunnel thực tế nếu máy bạn không có route
tới IP này. Tài khoản được tự đăng ký, không cần mật khẩu có sẵn.

API:

| Endpoint | Chức năng |
| --- | --- |
| GET /health | Trạng thái service |
| GET /search?q=book | Tìm sản phẩm, trả về id/name/description |
| POST /register | JSON username/password; username 3–64 ký tự, password 12–128 ký tự |
| POST /login | JSON username/password; trả session cookie |
| POST /notes | JSON body; cần cookie đăng nhập |
| GET /notes | Đọc note thuộc tài khoản hiện tại |

Mỗi vòng, checker tạo tài khoản riêng và cất flag trong note. Flag mới có dạng
`[A-Z0-9]{31}=`, bắt đầu bằng `S`.

Nhiệm vụ:

1. Tạo tài khoản, đăng nhập và tạo note riêng. Chứng minh một tài khoản khác
   không đọc được note của bạn qua API `/notes` thông thường.
2. Kiểm tra cách `/search` xử lý đầu vào; xác định SQL injection và số cột SELECT.
3. Trong sandbox được cấp, đọc được một note của checker bằng UNION injection.
4. Ghi lại request, dữ liệu quan sát được và nguyên nhân lộ dữ liệu.
5. Vá truy vấn tìm kiếm bằng tham số SQL; giữ đăng ký, đăng nhập, tìm kiếm hợp lệ
   và ghi/đọc note hoạt động.
6. Đưa bằng chứng checker vẫn OK sau khi vá, và request SQLi cũ không còn lộ note.

Tiêu chí: lỗ hổng có bằng chứng tái hiện; giải thích đúng ranh giới dữ liệu;
bản vá dùng tham số hóa; checker xác minh chức năng bình thường và flag còn nguyên.
Chỉ xóa/chặn endpoint hoặc trả giả `/health` không đạt yêu cầu.

Checker độc lập không phải nơi nộp flag. Giảng viên quyết định nộp báo cáo hay
dùng hệ thống chấm điểm; ForcAD là phần tích hợp riêng nếu tổ chức Attack–Defence.
