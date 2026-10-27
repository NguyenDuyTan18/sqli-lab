# Dùng checker với ForcAD hiện tại

`provisioning/files/checker.py` tương thích contract của source ForcAD đã xem:

```text
checker.py check HOST
checker.py put HOST FLAG_ID FLAG VULN
checker.py get HOST PRIVATE_FLAG_DATA FLAG VULN
```

`checker_type: pfr`: stdout PUT là public owner/note ID; stderr PUT là JSON private
username/password/note ID. Không dùng cấu hình hackerdom mặc định cho checker này,
vì ForcAD phải lấy private flag data từ stderr và public attack data từ stdout.

Trên máy ForcAD Linux, từ thư mục root ForcAD, copy checker của lab vào:

```bash
mkdir -p checkers/sqli_shop
cp /path/to/cyberrange-sqli-lab/provisioning/files/checker.py checkers/sqli_shop/checker.py
chmod 755 checkers/sqli_shop/checker.py
```

Không cần thêm thư viện vào `checkers/requirements.txt`, nhưng vẫn giữ file đó
vì Dockerfile của ForcAD yêu cầu. Tham khảo `integrations/forcad-config.yml.example`,
merge tasks/teams vào config hiện tại, sửa start_time trước khi setup/start.
Không gọi reset/clean trên game đang chạy.

## Truy cập từ Docker

IP `10.20.10.10` chỉ dùng được khi worker container có route đến sandbox.
SSH tunnel bind localhost Windows không tự xuất hiện trong container ForcAD.
Controller bên ngoài dùng SSH để kích hoạt checker trong sandbox và lưu JSON
kết quả ở máy điều khiển; luồng này độc lập với việc ForcAD ghi điểm.

Nếu muốn chính ForcAD chấm qua SSH management:

1. Chạy tunnel trên máy Linux chạy ForcAD, theo đúng management config.
2. Cho worker truy cập endpoint tunnel thông qua mạng riêng được kiểm soát.
3. Đặt `teams[].ip` thành `host:port` mà worker truy cập được; checker này hỗ trợ
   `HOST:PORT`. Kiểm tra model cấu hình ForcAD của phiên bản bạn đang chạy.
4. Với nhiều sandbox có cùng IP nội bộ, dùng tunnel/port và state riêng cho mỗi team.

Không đổi tunnel từ 127.0.0.1 sang 0.0.0.0 chỉ để container truy cập mà chưa cấu
hình giới hạn mạng. Việc nối worker Docker cần quyết định theo máy host/mạng thực tế.

ForcAD PFR là tích hợp chấm điểm riêng. Controller ngoài gọi checker VM qua SSH
để theo dõi dịch vụ trong cùng sandbox; không cần cho Docker worker truy cập SSH
tunnel của Windows. Nếu muốn ForcAD tự chấm, cấu hình route/IP theo phần trên.
