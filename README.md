# SQL injection lab cho CyberRangeCZ + checker bên ngoài

Thư mục này là một **sandbox definition độc lập** để đưa lên GitHub.
CyberRangeCZ đọc Git repository, dùng topology và Ansible provisioning để tạo
máy trên OpenStack. OpenStack không tự đọc GitHub repository này.

Đưa **nội dung của thư mục `cyberrange-sqli-lab` vào gốc repo mới**:
`topology.yml` phải nằm ngay ở root Git repository, không nằm trong thư mục con.

## Mô hình

```text
Windows của bạn
  external/start-checker.ps1 (schedule + SSH controller)
       |
       | SSH management command + JSON request/result
       v
  SSH management config -> Proxy Jump -> MAN -> checker VM
                                                  | HTTP nội bộ tới các service đã cấu hình
                                                  v
                            team/service targets trong cùng sandbox
```

Topology mẫu có 2 máy chức năng (`sqli-web`, `checker`) và 1 router (`lab-router`).
Khi một sandbox chứa dịch vụ của nhiều đội, thêm các máy/network cần thiết vào
topology và khai báo mỗi endpoint checker cần theo dõi.
Controller bên ngoài giữ chu kỳ và dùng SSH gọi checker VM. VM truy cập các dịch vụ
trong sandbox, giữ state riêng theo service ID, rồi trả trạng thái JSON qua SSH.
Mỗi service ID tạo tài khoản và flag riêng. Chỉ một controller nên điều phối
một sandbox tại một thời điểm.

- Web: Python + SQLite, tìm kiếm sản phẩm và ghi chú riêng tư.
- Lỗ hổng: UNION-based SQL injection ở `GET /search?q=...`.
- Checker: kiểm tra tìm kiếm hợp lệ, tạo tài khoản, ghi flag vào note,
  đăng nhập đọc lại flag, kiểm tra flag các vòng trước.
- Không có flag cố định hoặc mật khẩu quản trị phải đưa lên GitHub.
- Python 3.10+; ứng dụng/checker chỉ dùng standard library, không cần pip hay Docker.
- Đây là bài lab cố ý có lỗ hổng; triển khai trong mạng thực hành có kiểm soát.

## 1. Chuẩn bị image và đưa lên GitHub

Trong `topology.yml`, image đã đặt là `ubuntu-22.04`, có trong danh sách Images
bạn cung cấp. Xác nhận `mgmt_user: ubuntu` đúng với image đó và thay `flavor:
standard.small` bằng flavor tồn tại trên OpenStack của bạn. Cả ba image phải có
cloud-init, SSH và sudo; router cũng phải tương thích preconfig của hệ thống.
Cần truy cập APT hoặc mirror nội bộ khi provisioning cài Python.

Mạng mặc định: `10.20.10.0/24` và `10.20.20.0/24`. Nếu đổi, sửa topology và
cập nhật `sqli_checker_targets` trong `provisioning/group_vars/all.yml` cho mọi
service của các đội. Mỗi giá trị là `HOST:PORT` mà VM checker truy cập được.
Ví dụ với hai đội:

```yaml
sqli_checker_targets:
  team-a: "10.20.10.11:8080"
  team-b: "10.20.10.12:8080"
```

Topology mẫu tự lấy IP `sqli-web` từ inventory. Chọn dải không trùng mạng
management/WAN/mạng hiện có. `hidden` chỉ ẩn hiển thị, không phải ACL.

Tạo repo GitHub mới rồi upload nội dung thư mục này. Giữ đúng cấu trúc:

```text
topology.yml
provisioning/
  playbook.yml
  group_vars/all.yml
  files/app.py
  files/checker.py
  files/monitor.py
  files/remote_runner.py
  files/run-command
  templates/...
external/...
integrations/...
docs/...
tests/...
```

Không upload `ssh-access.zip`, SSH private key hoặc `runtime/`.
Repo có `.gitignore` cho các dữ liệu này. Repo private cần cấu hình quyền clone
cho CyberRange; không đặt GitHub token vào Git URL.

## 2. Tạo sandbox

1. CyberRange portal -> **Sandbox Definitions -> Create**.
2. Git URL: `https://github.com/<owner>/<repo>.git`.
3. Revision: branch thực tế, ví dụ `main`; sau khi chạy được nên chọn commit cụ thể.
4. Tạo Pool dùng definition này; cấp phát sandbox và chờ provisioning hoàn tất.
5. Kiểm tra có `sqli-web`, `checker`, `lab-router` trong topology.
6. Vào Pool, tải gói **SSH management access** dành cho instructor.

Không dùng file SSH user access để quản lý máy checker. Checker VM không tự lập
lịch: controller ngoài gọi nó theo chu kỳ. Controller gửi action và service ID;
runner chỉ tra địa chỉ từ allowlist cấu hình provisioning, không nhận target IP
hay shell command tùy ý.

## 3. Đặt SSH config/key trên máy Windows này

Chi tiết: [docs/SSH-WINDOWS.md](docs/SSH-WINDOWS.md).
Thư mục sử dụng trên máy hiện tại là **`C:\Users\Admin\.ssh`**.

Sau khi tải `ssh-access.zip`, chạy trong PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh" | Out-Null
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ssh-access.zip" -DestinationPath "$env:USERPROFILE\.ssh"
Get-ChildItem "$env:USERPROFILE\.ssh" -Filter '*management-config'
```

Nếu file trùng đã tồn tại, sao lưu/đối chiếu trước khi giải nén lại.
Giữ nguyên tên các file trong ZIP, bao gồm management key và `.pub`.
Đường dẫn thực tế thường là:

```text
C:\Users\Admin\.ssh\pool-id-<POOL>-sandbox-id-<SANDBOX>-management-config
C:\Users\Admin\.ssh\pool-id-<POOL>-management-key
C:\Users\Admin\.ssh\pool-id-<POOL>-management-key.pub
```

Tên do portal sinh có thể khác. Dùng tên được giải nén thực tế và kiểm tra
`IdentityFile` trong config trỏ đúng tới private key.

## 4. Điều phối checker bên trong từ Windows

Trong PowerShell, `cd` vào thư mục bài lab đã tải về. Thay đường dẫn config:

```powershell
.\external\start-checker.ps1 -SshConfig "$env:USERPROFILE\.ssh\pool-id-<POOL>-sandbox-id-<SANDBOX>-management-config" -Once
```

Lệnh này SSH vào alias `checker`, yêu cầu VM chạy `round` cho mọi service ID đã
khai báo trong `sqli_checker_targets`, nhận JSON tóm tắt kết quả qua stdout, và
lưu từng lượt vào `runtime/external-results.jsonl`. Chạy theo chu kỳ 60 giây:

```powershell
.\external\start-checker.ps1 -SshConfig "$env:USERPROFILE\.ssh\pool-id-<POOL>-sandbox-id-<SANDBOX>-management-config"
```

Script dùng `ssh.exe` của Windows:

1. Thử SSH và cho bạn xác minh host fingerprint ở lần đầu.
2. Gửi request JSON giới hạn qua SSH để VM checker thực hiện lượt kiểm tra.
3. Nhận JSON kết quả qua SSH và lưu log bên ngoài. Ctrl+C dừng chu kỳ.

Chạy chỉ health/search, không tạo flag mới:

```powershell
.\external\start-checker.ps1 -SshConfig "$env:USERPROFILE\.ssh\pool-id-<POOL>-sandbox-id-<SANDBOX>-management-config" -Action check -Targets sqli-web
```

Chọn một số đội/service ID bằng `-Targets team-a,team-b`; bỏ tùy chọn này để
chạy tất cả ID đã cấu hình. `-Action round` kiểm tra health/search, xác minh các
flag cũ, tạo flag mới rồi đọc lại để xác nhận. `-Action check` chỉ kiểm tra
health/search. `-Once` chạy đúng một lượt. Không cần HTTP tunnel hay mở cổng vào
checker VM.

Flag/password và state integrity được giữ trong `/var/lib/sqli-checker/targets/`
trên VM checker; dữ liệu xuất ra ngoài chỉ gồm thời gian, service ID, trạng thái,
số flag cũ đã xác minh và lỗi checker. Không chia sẻ state trong VM. Mỗi sandbox
cần file log `runtime/external-results.jsonl` riêng. Nếu sandbox bị tạo lại,
state cũ trong VM mất theo máy cũ; giữ log bên ngoài để đối chiếu.

## 5. Học viên và giảng viên

- [Đề bài và tiêu chí hoàn thành](docs/STUDENT.md)
- [Hướng dẫn giảng viên: SQLi và cách vá](docs/INSTRUCTOR.md)
- [Gắn vào ForcAD bên ngoài range](docs/FORCAD.md)

Monitor báo availability/integrity, không tự tạo leaderboard hay chấm
flag học viên nộp. Muốn tính điểm Attack–Defence, dùng ForcAD với checker PFR.
Phần Training Definition/Training Run của CyberRange được tạo riêng nếu cần
giao diện phân cấp độ và chấm bài của portal; repo này cung cấp Sandbox Definition.

## 6. Chạy thử hoàn toàn local, trước khi có OpenStack

Terminal 1:

```powershell
py provisioning/files/app.py --db runtime/local-lab.db
```

Terminal 2:

```powershell
.\external\run-once.ps1 -Target 127.0.0.1:8080
```

Chạy kiểm thử:

```powershell
py -m unittest discover -s tests -v
```

Trên Linux thay `py` bằng `python3`. Xem kết quả đã kiểm tra và các phần cần
xác nhận trên OpenStack thật trong [docs/VALIDATION.md](docs/VALIDATION.md).

## Tài liệu định dạng chính thức

- [Sandbox Definition](https://docs.platform.cyberrange.cz/user-guide-advanced/sandboxes/sandbox-definition/)
- [Topology Definition](https://docs.platform.cyberrange.cz/user-guide-advanced/sandboxes/topology-definition/)
- [Sandbox Provisioning](https://docs.platform.cyberrange.cz/user-guide-advanced/sandboxes/sandbox-provisioning/)
- [Sandbox Access / SSH management](https://docs.platform.cyberrange.cz/user-guide-advanced/sandboxes/sandbox-access/)
- [Import Git URL và Revision](https://docs.platform.cyberrange.cz/user-guide-basic/sandbox-agenda/sandbox-definition/)
