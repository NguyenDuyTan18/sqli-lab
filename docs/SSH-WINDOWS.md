# SSH management trên Windows

Máy hiện tại dùng `C:\Users\Admin\.ssh`. Không đặt key bên trong thư mục bài
đưa lên GitHub. Chờ tạo sandbox và tải ZIP thật rồi mới làm các bước này.

## Lưu đúng file

Tải **management access** từ Pool bằng tài khoản instructor, giải nén toàn bộ
ZIP vào `$env:USERPROFILE\.ssh`. Không đổi tên key, không ghép config vào
`~/.ssh/config`; sử dụng `ssh -F <file>` để chọn đúng sandbox.

```powershell
$config = "$env:USERPROFILE\.ssh\pool-id-<POOL>-sandbox-id-<SANDBOX>-management-config"
Test-Path -LiteralPath $config
ssh -F $config -G checker | Select-String 'hostname|user |identityfile|proxyjump|proxycommand'
```

`-G` chỉ hiển thị cấu hình SSH hiệu lực, chưa kết nối. So sánh `Host` trong file
thật với `checker`/`man` trong các ví dụ. Giữ nguyên ProxyJump hoặc ProxyCommand
mà CyberRange tạo; chúng thể hiện tuyến qua gateway và MAN.

Nếu các đường dẫn `IdentityFile` là đường dẫn Linux không đúng trên Windows,
sửa **bản config được tải riêng** để dùng đường dẫn Windows với dấu `/`, ví dụ:

```sshconfig
IdentityFile C:/Users/Admin/.ssh/pool-id-<POOL>-management-key
```

Sửa mọi tham chiếu tới key/config trong ProxyCommand nếu có. Không sửa các
IP/username do portal cấp theo suy đoán. Nếu cấu hình sinh ra dùng tiện ích shell
Linux mà `ssh.exe` không chạy được, dùng WSL với ZIP/config giải nén trong
`~/.ssh` của WSL. Script PowerShell cần config chạy được bằng `ssh.exe` trên
Windows; khả năng này cần kiểm tra với ZIP thật của instance.

## Thử kết nối

```powershell
ssh -F $config man true
ssh -F $config checker true
```

Xác minh fingerprint của `man` và `checker` với quản trị viên khi kết nối lần
đầu. Không dùng `StrictHostKeyChecking=no`. Nếu sandbox được tạo lại và host key
thay đổi, đối chiếu instance/fingerprint trước khi sửa known_hosts.

Nếu OpenSSH báo private key có quyền quá rộng, hạn chế ACL của **đúng file key**
đã tải (không áp dụng đệ quy cho thư mục `.ssh`):

```powershell
$key = "$env:USERPROFILE\.ssh\pool-id-<POOL>-management-key"
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
icacls $key /inheritance:r
icacls $key /grant:r "${identity}:(R)"
```

Nếu key có ACL cấp trực tiếp cho người dùng khác, kiểm tra `icacls $key`
và nhờ quản trị viên sửa đúng ACL. Không đưa nội dung private key vào chat.

## Chạy controller ngoài

Từ thư mục lab, chạy một vòng `round` cho mọi service ID:

```powershell
cd C:\path\to\cyberrange-sqli-lab
.\external\start-checker.ps1 -SshConfig $config -Once
```

Controller SSH vào alias `checker`. Checker VM dùng các target đã cấu hình tại
`provisioning/group_vars/all.yml`, kiểm tra dịch vụ trong sandbox, rồi trả JSON
kết quả qua stdout SSH. Controller ghi log ở
`runtime/external-results.jsonl`. Chạy theo chu kỳ 60 giây:

```powershell
.\external\start-checker.ps1 -SshConfig $config -Interval 60
```

Chỉ kiểm tra health/search hoặc chọn service IDs:

```powershell
.\external\start-checker.ps1 -SshConfig $config -Action check -Targets team-a,team-b
```

Mỗi service ID phải có trong `sqli_checker_targets`; controller không gửi địa chỉ
IP tùy ý hay shell command. Dữ liệu flag/password ở lại state riêng trên checker
VM; JSON về ngoài chỉ chứa trạng thái và thông tin chẩn đoán. Nếu chạy SSH bằng
WSL, chạy controller trong cùng môi trường SSH có management config.

Muốn mở web thủ công để xem bài, dùng tunnel riêng trong một terminal:

```powershell
ssh -F $config -N -T -L 127.0.0.1:18080:10.20.10.10:8080 checker
```

Sau đó truy cập `http://127.0.0.1:18080/`. Tunnel này phục vụ trình duyệt,
không tham gia chu kỳ checker.

Nếu lệnh không chạy được, kiểm tra đường dẫn config, alias `checker`, quyền sudo
command giới hạn và log dịch vụ web (`journalctl -u sqli-web`) trên máy lab.
