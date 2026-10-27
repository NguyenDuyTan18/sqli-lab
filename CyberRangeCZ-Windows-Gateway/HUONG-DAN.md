# Hướng dẫn truy cập ServiceDesk qua Windows Gateway

Tài liệu này cấu hình máy Windows `10.13.145.42` làm SSH Gateway để mở các ServiceDesk trong CyberRangeCZ cho máy trong LAN trường. Máy thí sinh chỉ cần trình duyệt; không cần cài SSH hoặc VPN.

## Sơ đồ cổng

| URL trên Gateway | Máy đích trong sandbox | Dịch vụ |
| --- | --- | --- |
| `http://10.13.145.42:8080/` | `10.80.0.20:80` | ServiceDesk dùng chung trên server |
| `http://10.13.145.42:8011/` | `10.80.0.11:8080` | ServiceDesk đội 1 |
| `http://10.13.145.42:8012/` | `10.80.0.12:8080` | ServiceDesk đội 2 |
| `http://10.13.145.42:8013/` | `10.80.0.13:8080` | ServiceDesk đội 3 |
| `http://10.13.145.42:8014/` | `10.80.0.14:8080` | ServiceDesk đội 4 |

Các dịch vụ trên bốn máy attacker chỉ xuất hiện sau khi provisioning phiên bản mới nhất chạy thành công. Mật khẩu web riêng của từng máy nằm trong `~/lab-addresses.txt` trên VM tương ứng; tài khoản đăng nhập web là `alice`. Provisioning lại sẽ tạo mật khẩu mới.

## SSH config đang dùng

Đã tìm thấy bộ SSH mới của pool 93 ở `E:\Google\user-ssh-access` và sao chép config cùng key tương ứng vào `%USERPROFILE%\.ssh`. Alias là `man`, địa chỉ MAN là `192.168.67.140`, ProxyJump là `10.32.8.175`.

`config.json` đã trỏ đến config mới:

```text
%USERPROFILE%\.ssh\pool-id-93-sandbox-id-e4ac3f75-8eff-4cf9-aeea-f09e9d63189c-user-config
```

Không chép private key vào repository và không gửi key cho thí sinh.

## Kiểm tra trước khi mở tunnel

Mở PowerShell tại thư mục `CyberRangeCZ-Windows-Gateway`:

```powershell
Test-NetConnection 10.13.145.42 -Port 8011
Test-NetConnection 10.32.8.175 -Port 22
.\Test-CTFGateway.ps1
```

Máy Windows hiện phải có IP `10.13.145.42`; cổng 8011–8014 phải được Windows Firewall cho phép. SSH tới jump host phải thông suốt trước khi khởi động tunnel. Nếu đây là allocation mới, hãy xác minh fingerprint host key của jump host và MAN với quản trị viên CyberRangeCZ trước khi chấp nhận. Không tắt kiểm tra host key.

Kiểm tra provisioning đã cài ServiceDesk trên mỗi attacker bằng trang `/health` qua tunnel hoặc từ một máy có quyền truy cập sandbox. Nếu cổng `10.80.0.11–14:8080` chưa lắng nghe, cần chạy provisioning từ nhánh `main` mới nhất rồi mới đổi tunnel sang các cổng này.

## Khởi chạy và kiểm tra

Sau khi SSH hoạt động, fingerprint đã được xác minh, và các dịch vụ đích đã sẵn sàng, chạy:

```powershell
.\Start-CTFGateway.ps1
```

Giữ cửa sổ PowerShell này mở. Script theo dõi kết nối và tự thử kết nối lại tối đa số lần đặt trong `config.json`. Từ Gateway, kiểm tra:

```powershell
Get-NetTCPConnection -LocalAddress 10.13.145.42 -LocalPort 8080,8011,8012,8013,8014 -State Listen
curl.exe -i http://10.13.145.42:8080/
curl.exe -i http://10.13.145.42:8011/
curl.exe -i http://10.13.145.42:8012/
curl.exe -i http://10.13.145.42:8013/
curl.exe -i http://10.13.145.42:8014/
```

Từ máy thí sinh, chạy `Test-NetConnection 10.13.145.42 -Port 8011` rồi mở URL tương ứng trong bảng trên. Muốn dừng tunnel, chạy `.\Stop-CTFGateway.ps1` từ cửa sổ PowerShell khác.

## Trạng thái hiện tại

- SSH config và key pool 93 đã được sao chép vào thư mục `.ssh` của Windows; `config.json` dùng config này. Host key jump host và MAN đã được xác minh, lưu trong `runtime/known_hosts` riêng cho Gateway.
- Tunnel đang chạy dưới tiến trình SSH `131092`, bind vào `10.13.145.42` trên các cổng 8080, 8011, 8012, 8013 và 8014.
- Kiểm tra lúc 11:39 ngày 20/10/2026: preflight SSH forwarding thành công tới cả năm dịch vụ và cả năm URL đều trả HTTP 200 từ Gateway.
- Windows Firewall đang bật 5 rule inbound TCP cho `8080, 8011–8014`, `RemoteAddress 0.0.0.0/0`. Từ máy thí sinh, hãy thử `Test-NetConnection 10.13.145.42 -Port 8011` và mở URL tương ứng; chưa có kết quả kiểm tra từ máy thí sinh trong phiên này.
- Không có lệnh provisioning hay thay đổi nào được thực hiện trên sandbox trong lượt cấu hình này.

Muốn dừng tunnel, chạy `.\Stop-CTFGateway.ps1` trong cửa sổ PowerShell khác. Muốn khởi động lại sau đó, chạy `.\Start-CTFGateway.ps1` từ thư mục này.
