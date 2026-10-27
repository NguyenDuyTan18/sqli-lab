# Giảng viên: nội dung và đáp án

Ứng dụng dùng SQLite chung cho bảng products, users, sessions, notes. Chỉ một
điểm cố ý dễ bị SQL injection là truy vấn `/search`; đăng nhập và ghi/đọc note
thông thường dùng parameter binding. Mật khẩu được hash có salt.

Luồng khai thác dành cho service lab:

```sql
' UNION SELECT id, owner, body FROM notes -- 
```

Ba cột của products và notes tương thích; phần comment bỏ dấu đóng của truy vấn
gốc. Nội dung note sẽ xuất hiện trong `description` của JSON kết quả.
Ví dụ trong PowerShell, khi tunnel thủ công đang chạy (xem
`docs/SSH-WINDOWS.md`):

```powershell
$payload = "' UNION SELECT id, owner, body FROM notes -- "
$query = [uri]::EscapeDataString($payload)
Invoke-RestMethod "http://127.0.0.1:18080/search?q=$query" | ConvertTo-Json -Depth 5
```

Phải chạy ít nhất một vòng checker để có flag. Không seed một flag cố định
vào Git. Checker sinh ngẫu nhiên tài khoản/password/flag lúc runtime.

## Vá

Thay nối chuỗi SELECT bằng:

```python
connection.execute(
    'SELECT id, name, description FROM products WHERE name LIKE ?',
    ('%' + query + '%',),
)
```

Ứng dụng có `--fixed` để giảng viên đối chiếu kết quả. Trên local:

```powershell
py provisioning/files/app.py --db runtime/local-lab.db --fixed
```

Trên sandbox, giảng viên có thể đặt `sqli_search_fixed: true` trong
`provisioning/group_vars/all.yml` và chạy lại provisioning, hoặc để học viên sửa
mã trên VM và restart `sqli-web`. Đổi repository revision cần được áp dụng theo
quy trình pool/sandbox của instance; chỉ push Git không tự cập nhật VM đang chạy.
Không xóa file DB khi đổi sang chế độ fixed.

## Quan sát checker

Controller bên ngoài ghi kết quả JSON mỗi lượt vào
`runtime/external-results.jsonl`. Mỗi kết quả ghi thời gian, action, service ID,
trạng thái, số flag cũ đã kiểm tra và lỗi; không ghi password hay flag. Trên
checker VM, state riêng từng service ID nằm trong
`/var/lib/sqli-checker/targets/` và chỉ service user `sqli-checker` đọc/ghi được.
Giữ state nguyên vẹn khi điều tra lỗi integrity.

Mỗi service ID có state riêng và mặc định giữ tối đa 5 flag để kiểm tra.
Checker VM khóa lượt chạy để tránh hai controller ghi cùng lúc. `keep=5` là số
flag lưu để kiểm tra, không phải hệ thống tiếp nhận flag hay TTL của ForcAD. Nếu
flag mất, checker giữ state cũ và tiếp tục báo FAIL để giảng viên điều tra.

Code exit của checker tương thích Hackerdom: 101 OK, 102 CORRUPT,
103 MUMBLE, 104 DOWN, 110 CHECK_FAILED. `monitor.py --once` đổi về exit 0/1;
checker.py chạy thành công trả 101, không phải 0.

## Giới hạn vận hành

Service WSGI dùng standard library, dành cho lớp lab nhỏ, không phải production
web server. Dữ liệu người dùng/notes tích lũy để phục vụ điều tra trong buổi học;
buổi học mới nên tạo sandbox mới. Không tự xóa toàn bộ DB khi học viên đang làm.
Không công khai endpoint có lỗ hổng ra Internet; checker chỉ nhận SSH command
được giới hạn, không mở HTTP listener, và state nằm trên filesystem riêng.
