# SQLi ServiceDesk — CyberRangeCZ

Bài thực hành có chủ đích chứa SQL injection trong chức năng tìm kiếm sau đăng nhập. Chỉ triển khai trong sandbox huấn luyện riêng; không đưa ứng dụng ra mạng công cộng. Các URL trực tiếp của phiếu kiểm tra quyền sở hữu. Mỗi máy đội có một cơ sở dữ liệu và mật khẩu riêng.

## Triển khai

Đặt toàn bộ thư mục này tại gốc Git repository dành cho CyberRangeCZ, tạo Sandbox Definition, pool kích thước 1 và allocate sandbox. Import `training-definition.json` và liên kết Training Instance. Topology gồm `attacker1`–`attacker4` (`10.80.0.11`–`.14`) và server (`10.80.0.20`). Các máy đội chạy ServiceDesk trên cổng 8080; server bị chặn kết nối khởi tạo từ máy đội. Trainee đăng nhập Linux `user-access` bằng thông tin trong định nghĩa; mật khẩu ServiceDesk của đội nằm trong `~/lab-addresses.txt`.

Ansible yêu cầu `global_sandbox_id` và khóa công khai `global_ssh_public_user_key` do nền tảng cấp. Playbook tự cài checker trong vào `/opt/idor-free-lab/sqli-checker.py` cho mỗi máy đội, tạo cấu hình `~user-access/.sqli-checker.json` quyền 0600 và chạy kiểm tra sau khi ứng dụng khởi động. Nếu dịch vụ, đăng nhập hoặc SQLi không đáp ứng, provisioning thất bại. Playbook vẫn kiểm tra chính sách mạng hiện có.

## Checker ngoài và SSH

`checker/external.py` là chương trình dành cho môi trường CyberRange có Python 3, OpenSSH client, đường SSH tới máy đội, khóa riêng tương ứng với `global_ssh_public_user_key` và host key SSH đã xác thực. Khóa riêng không được ghi vào repository hoặc sandbox. Ví dụ chạy trên môi trường đó:

```sh
python3 checker/external.py --host 10.80.0.11 --key /secure/path/platform-key --known-hosts /secure/path/known_hosts
```

Lặp lại cho từng địa chỉ đội; `--port` thay đổi cổng SSH nếu cần. Checker ngoài SSH với user `user-access`, kiểm tra host key nghiêm ngặt, chạy checker trong bằng lệnh cố định và xuất một JSON. Không tự động tin host key: cần xác minh và cài `known_hosts` từ nguồn tin cậy của hệ thống. SSH phải truy cập được địa chỉ đích từ nơi chạy checker; ACL hiện có chỉ chặn máy đội kết nối đến server.

Ví dụ thành công:

```json
{"identity":"SANDBOX_UUID-attacker1","service":"up","authentication":"ok","sqli":"vulnerable"}
```

`service`: `up`, `down`, `identity_mismatch`, hoặc `unknown`; `authentication`: `ok`, `failed`, hoặc `unknown`; `sqli`: `vulnerable`, `not_detected`, hoặc `unknown`. `not_detected` nghĩa là phép thử không quan sát được lỗi, không phải chứng minh ứng dụng an toàn. Trạng thái không xác định có thể do lỗi SSH, cấu hình, HTTP hoặc dữ liệu; exit code khác 0 báo lỗi kiểm tra/kết nối, không dùng làm điểm. Các kiểm tra không sửa dữ liệu.

Checker ngoài là CLI tích hợp, chưa tự đăng ký hoặc tự chạy định kỳ trong CyberRange: repository mẫu không cung cấp API, thông tin host, lịch chạy, đường dẫn khóa riêng, host key hoặc cơ chế hook của môi trường CyberRange cụ thể. Quản trị viên cần gắn lệnh trên vào runner/scheduler của CyberRange và cung cấp các thông số đó. Không sao chép khóa riêng vào máy đội. Không suy diễn `global_ssh_public_user_key` là đường dẫn khóa riêng.

## Kiểm thử mã nguồn

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
```

Các tài liệu còn lại trong `docs/` và thư mục gateway là tài liệu IDOR/mạng của mẫu gốc, chỉ dùng tham khảo topology; nội dung bài tập IDOR trong đó không mô tả bài SQLi mới. Triển khai và SSH end-to-end cần được xác nhận trên CyberRange thực tế.
