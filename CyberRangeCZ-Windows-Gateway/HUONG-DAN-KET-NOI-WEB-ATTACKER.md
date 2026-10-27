# Đưa các web ServiceDesk của attacker qua Windows Gateway

Tài liệu này hướng dẫn cách cho máy trong LAN mở web ServiceDesk của từng đội qua máy Windows `10.13.145.42`. Máy thí sinh chỉ cần trình duyệt, không cần SSH hoặc VPN.

## 1. Sơ đồ kết nối

```text
Máy thí sinh trong LAN
        │ HTTP tới 10.13.145.42:8011–8014
        ▼
Windows Gateway 10.13.145.42
        │ SSH local port forwarding qua ProxyJump MAN
        ▼
CyberRangeCZ MAN → các VM attacker trong sandbox
```

| Cổng trên Windows | VM đích | Cổng web đích | URL thí sinh dùng |
| ---: | --- | ---: | --- |
| 8011 | attacker1 `10.80.0.11` | 8080 | `http://10.13.145.42:8011/` |
| 8012 | attacker2 `10.80.0.12` | 8080 | `http://10.13.145.42:8012/` |
| 8013 | attacker3 `10.80.0.13` | 8080 | `http://10.13.145.42:8013/` |
| 8014 | attacker4 `10.80.0.14` | 8080 | `http://10.13.145.42:8014/` |

Các cổng `8011–8014` là cổng nghe trên Windows. Tunnel chuyển tiếp mỗi cổng tới cổng `8080` của VM tương ứng. Địa chỉ `10.80.0.11–14` không cần và thường không thể mở trực tiếp từ máy thí sinh.

## 2. Điều kiện đã cấu hình trên Gateway

- SSH config pool 93 nằm trong `%USERPROFILE%\.ssh`; `config.json` dùng alias `man` và config pool này.
- MAN được truy cập qua SSH jump host `10.32.8.175`; host key được xác minh và lưu trong `runtime\known_hosts` riêng.
- `config.json` khai báo bốn dịch vụ và ánh xạ cổng `8011–8014` tới VM attacker.
- Windows Firewall có inbound TCP rules bật cho `8080, 8011, 8012, 8013, 8014`. Phạm vi nguồn hiện tại là `0.0.0.0/0`, tức mọi nguồn IPv4 có đường định tuyến tới Gateway.
- Không đưa private key vào thư mục dự án hoặc chia sẻ cho thí sinh.

## 3. Khởi chạy tunnel

Mở PowerShell trên Windows Gateway và chạy:

```powershell
Set-Location 'C:\Users\Admin\Desktop\idor-c-main\CyberRangeCZ-Windows-Gateway'
.\Start-CTFGateway.ps1
```

Giữ cửa sổ PowerShell quản lý tunnel mở. Script tạo tiến trình `ssh.exe` riêng, ghi log vào `logs\`, theo dõi kết nối và thử kết nối lại theo giới hạn trong `config.json`.

Nếu script báo cổng đã được sử dụng, kiểm tra tunnel hiện tại trước khi khởi chạy lần nữa:

```powershell
Get-NetTCPConnection -State Listen -LocalAddress 10.13.145.42 -LocalPort 8011,8012,8013,8014
```

Để dừng tunnel do script quản lý, mở một cửa sổ PowerShell khác tại cùng thư mục và chạy:

```powershell
.\Stop-CTFGateway.ps1
```

## 4. Kiểm tra từ Windows Gateway

Xem các cổng đang lắng nghe:

```powershell
Get-NetTCPConnection -State Listen -LocalAddress 10.13.145.42 -LocalPort 8011,8012,8013,8014
```

Gửi request HTTP tới từng dịch vụ:

```powershell
curl.exe -i http://10.13.145.42:8011/
curl.exe -i http://10.13.145.42:8012/
curl.exe -i http://10.13.145.42:8013/
curl.exe -i http://10.13.145.42:8014/
```

Có phản hồi HTTP, ví dụ `HTTP/1.0 200 OK`, cho biết HTTP đã đi qua tunnel tới web service. Lần kiểm tra gần nhất trên Gateway cho kết quả HTTP 200 ở cả bốn cổng và preflight SSH forwarding thành công.

## 5. Kiểm tra từ máy thí sinh

Trên một máy khác trong LAN, mở PowerShell:

```powershell
Test-NetConnection 10.13.145.42 -Port 8011
```

`TcpTestSucceeded : True` xác nhận máy đó tới được cổng Gateway. Sau đó mở URL của đội tương ứng từ bảng ở trên. Nếu TCP thành công nhưng trang web không tải, kiểm tra tunnel, log và trạng thái web service đích. Nếu TCP thất bại, kiểm tra firewall, đường truyền LAN và Wi-Fi client isolation.

## 6. Kỹ thuật đang sử dụng

### SSH local port forwarding (`-L`)

Mỗi forward có dạng:

```text
<IP bind trên Windows>:<cổng nghe>:<IP VM trong sandbox>:<cổng dịch vụ>
```

Ví dụ ánh xạ đội 1:

```text
10.13.145.42:8011:10.80.0.11:8080
```

Khi trình duyệt truy cập `10.13.145.42:8011`, SSH chuyển luồng TCP từ cổng 8011 của Windows tới `10.80.0.11:8080`. Một phiên SSH có thể mang nhiều forward cùng lúc, vì vậy bốn đội dùng chung một tunnel nhưng có cổng riêng.

### ProxyJump

Alias `man` trong SSH config đi qua jump host `10.32.8.175` để tới MAN. MAN có đường mạng vào sandbox. Windows không cần route trực tiếp tới các VM `10.80.0.11–14`; luồng được chuyển tiếp bên trong phiên SSH.

### Bind vào IP Gateway cụ thể

Các forward bind vào `10.13.145.42`, là IP LAN của Windows. Máy trong LAN có thể truy cập đúng địa chỉ này; dịch vụ không bị bind tùy tiện trên mọi interface của Windows.

### Windows Firewall inbound

SSH tạo listener ở phía Windows; Windows Firewall quyết định máy khác có thể kết nối tới các listener đó hay không. Rules hiện cho phép TCP `8011–8014` từ `0.0.0.0/0`. Giới hạn này rộng: nếu cần chỉ cho thí sinh truy cập, thay bằng subnet hoặc danh sách IP đã được quản trị viên LAN xác nhận.

### Xác minh host key và kiểm tra kết nối

Gateway dùng kho `runtime\known_hosts` riêng và kiểm tra host key của jump host/MAN. Không dùng `StrictHostKeyChecking=no`. Script kiểm tra cổng, trạng thái tunnel và backend; khi SSH mất kết nối, script thử kết nối lại theo số lần giới hạn trong `config.json`.

## 7. Thêm hoặc đổi dịch vụ

Sửa một mục trong `config.json`, ví dụ:

```json
{
  "name": "attacker1 ServiceDesk",
  "protocol": "http",
  "gatewayPort": 8011,
  "sandboxIp": "10.80.0.11",
  "sandboxPort": 8080
}
```

Mỗi dịch vụ cần cổng Gateway duy nhất và IP/cổng đích đúng theo topology cùng cấu hình dịch vụ đang triển khai. Nếu đổi cổng Gateway, cần có inbound firewall rule tương ứng trước khi máy thí sinh truy cập được. Khởi động lại tunnel để nạp cấu hình mới.

## 8. Phạm vi thay đổi

Thiết lập này chỉ tạo SSH tunnel và firewall rules trên máy Windows Gateway. Nó không sửa topology, không chạy provisioning và không thay đổi các VM sandbox đang chạy.
