# Giải thích chi tiết: đưa dịch vụ CyberRangeCZ ra mạng LAN qua Windows Gateway

> Tài liệu này mô tả cấu hình trong thư mục `CyberRangeCZ-Windows-Gateway`. “Đưa ra mạng trường” ở đây nghĩa là máy khách có đường mạng tới Windows Gateway có thể mở các cổng được cấu hình. Đây không phải là public website trên Internet.

## 1. Sơ đồ đường đi của kết nối

```text
Trình duyệt máy thí sinh
  │ HTTP tới 10.13.145.42:8011 (hoặc 8012–8014, 8080)
  ▼
Mạng LAN / mạng có route tới Gateway
  ▼
Windows Gateway: 10.13.145.42
  ├─ Windows Defender Firewall cho phép TCP tới cổng được mở
  └─ OpenSSH giữ listener và chuyển từng kết nối vào SSH tunnel
       │ SSH mã hóa; dùng cấu hình host man và ProxyJump
       ▼
CyberRangeCZ Proxy Jump / MAN
  ├─ 10.80.0.11:8080  attacker1 ServiceDesk ── trả về qua tunnel
  ├─ 10.80.0.12:8080  attacker2 ServiceDesk ── trả về qua tunnel
  ├─ 10.80.0.13:8080  attacker3 ServiceDesk ── trả về qua tunnel
  ├─ 10.80.0.14:8080  attacker4 ServiceDesk ── trả về qua tunnel
  └─ 10.80.0.20:80    ServiceDesk chung      ── trả về qua tunnel
```

Máy thí sinh chỉ kết nối tới IP và cổng Windows Gateway. SSH client, private key và thông tin truy cập CyberRangeCZ chỉ nằm trên Windows Gateway; máy thí sinh không cần SSH, VPN hay phần mềm của CyberRangeCZ.

## 2. Quy trình cấu hình triển khai từng bước

Thực hiện lần lượt trên Windows Gateway. Các lệnh dưới đây chỉ là hướng dẫn; tài liệu này không tự chạy tunnel hoặc thay đổi Windows Firewall.

### Bước 1 — Xác nhận IP Gateway

Mở PowerShell và kiểm tra IP trên adapter đang nối LAN trường:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -eq '10.13.145.42' } |
  Select-Object InterfaceAlias,IPAddress,PrefixLength,AddressState
```

Kết quả cần có địa chỉ `10.13.145.42` ở trạng thái `Preferred`. Nếu không thấy, dừng ở đây: kiểm tra adapter, DHCP reservation/IP tĩnh với quản trị viên mạng và sửa `gatewayIp` chỉ khi IP được đổi có chủ đích. Không lấy subnet mask của Gateway làm allowlist thí sinh nếu quản trị viên chưa xác nhận.

### Bước 2 — Xác nhận máy thí sinh được phép truy cập

Hỏi quản trị viên mạng subnet CIDR cụ thể (ví dụ dạng `10.x.x.x/yy`) hoặc danh sách IP máy thí sinh. Chỉ nhập giá trị đã được xác nhận vào `allowedClientSubnets`. Cấu hình hiện tại là `0.0.0.0/0`, tức toàn bộ IPv4 có thể định tuyến tới Gateway; đây không phải giới hạn riêng cho LAN trường.

Ví dụ **chỉ khi** quản trị viên xác nhận đúng subnet `10.13.144.0/20` (đây là ví dụ minh họa, không mặc định là subnet thực tế):

```json
"allowedClientSubnets": ["10.13.144.0/20"]
```

Nếu có nhiều subnet được duyệt, liệt kê từng dải:

```json
"allowedClientSubnets": ["<CIDR-đã-xác-nhận-1>", "<CIDR-đã-xác-nhận-2>"]
```

Thay placeholder bằng CIDR hợp lệ trước khi lưu. Không giữ `0.0.0.0/0` nếu yêu cầu thực tế là chỉ cho máy trong LAN trường.

### Bước 3 — Cập nhật `config.json`

Mở `CyberRangeCZ-Windows-Gateway\config.json` trong trình soạn thảo văn bản. Đối chiếu với cấu hình đang dùng; những giá trị hiện có là:

```json
{
  "gatewayIp": "10.13.145.42",
  "sshConfig": "%USERPROFILE%\\.ssh\\pool-id-95-sandbox-id-d8aa60ef-4768-4588-9dea-4680da264c8a-user-config",
  "sshHost": "man",
  "allowedClientSubnets": ["0.0.0.0/0"],
  "maxRestartAttempts": 5,
  "restartDelaySeconds": 5,
  "healthCheckIntervalSeconds": 15,
  "startupTimeoutSeconds": 15,
  "services": [
    { "name": "IDOR ServiceDesk (from topology.yml)", "protocol": "http", "gatewayPort": 8080, "sandboxIp": "10.80.0.20", "sandboxPort": 80 },
    { "name": "attacker1 ServiceDesk", "protocol": "http", "gatewayPort": 8011, "sandboxIp": "10.80.0.11", "sandboxPort": 8080 },
    { "name": "attacker2 ServiceDesk", "protocol": "http", "gatewayPort": 8012, "sandboxIp": "10.80.0.12", "sandboxPort": 8080 },
    { "name": "attacker3 ServiceDesk", "protocol": "http", "gatewayPort": 8013, "sandboxIp": "10.80.0.13", "sandboxPort": 8080 },
    { "name": "attacker4 ServiceDesk", "protocol": "http", "gatewayPort": 8014, "sandboxIp": "10.80.0.14", "sandboxPort": 8080 }
  ]
}
```

Chú ý:

- `sshConfig` phải là file **user SSH config** đúng với pool/sandbox đang chạy; `%USERPROFILE%` được script mở rộng theo tài khoản Windows hiện tại. Sau khi pool đổi, thay đường dẫn bằng config mới và kiểm tra `IdentityFile` trong chính file đó trỏ tới private key tương ứng.
- `sshHost` phải khớp chính xác một mục `Host` trong config; cấu hình hiện tại dùng alias `man`. Không thay bằng IP jump host theo suy đoán.
- `sandboxIp` và `sandboxPort` phải khớp topology cùng cổng ứng dụng đã cài/running. Cấu hình hiện tại giả định ServiceDesk từng đội chạy ở port 8080 trên bốn attacker VM. Nếu sandbox chưa được provision ứng dụng đó, tunnel không thể tự cài ứng dụng.
- Mỗi `gatewayPort` phải duy nhất và còn trống. Chỉnh sửa JSON đúng dấu phẩy/ngoặc; tránh lưu mật khẩu hoặc private key trong file.

Sau khi lưu, có thể kiểm tra JSON parse được mà không khởi chạy tunnel:

```powershell
Get-Content .\config.json -Raw | ConvertFrom-Json | Out-Null
if ($?) { 'config.json: JSON hợp lệ' }
```

### Bước 4 — Kiểm tra SSH config, key path và host key

Chạy kiểm tra cấu hình gateway:

```powershell
Set-Location 'C:\Users\Admin\Desktop\idor-c-main\CyberRangeCZ-Windows-Gateway'
.\Test-CTFGateway.ps1
```

Trong log, kiểm tra các dòng nêu OpenSSH Client, alias `man`, ProxyJump và `IdentityFile exists=True`. Log chỉ được in đường dẫn key, không in nội dung key. Nếu alias không tìm thấy, config/key không tồn tại hoặc host key bị từ chối, xử lý lỗi đó trước; không chạy Start để bỏ qua kiểm tra.

Nếu pool/host mới, đối chiếu fingerprint của jump host và MAN qua kênh quản trị CyberRangeCZ. Chỉ chấp nhận fingerprint đã đối chiếu. Không đặt `StrictHostKeyChecking=no`, không xóa known_hosts để né cảnh báo. Sau khi host key hợp lệ được ghi vào kho `runtime\known_hosts` riêng, kiểm tra kết nối forward tới tất cả backend:

Nếu OpenSSH hỏi xác nhận host key cho allocation mới, sau khi đối chiếu fingerprint với quản trị viên có thể mở forward thử chỉ trên loopback. Chạy lệnh sau trong thư mục gateway; khi terminal hiển thị fingerprint, so sánh từng host với giá trị đã xác nhận. Nhập `yes` chỉ khi khớp, nếu không khớp nhấn `Ctrl+C`:

```powershell
ssh.exe -F .\runtime\ssh-safe.conf -N `
  -L 127.0.0.1:18080:10.80.0.20:80 `
  man
```

Khi lệnh giữ kết nối và không báo lỗi, known_hosts riêng đã nhận host key đã xác minh; nhấn `Ctrl+C` để dừng forward thử. Lệnh này bind vào `127.0.0.1`, không công bố cổng thử cho LAN. Sau đó tiếp tục kiểm tra các backend:

```powershell
.\Test-CTFGateway.ps1 -CheckSsh
```

Lệnh này kiểm tra SSH forward tạm trên loopback, không mở cổng ra LAN và không sửa firewall. Cần xử lý lỗi nếu một trong các backend không nhận TCP.

### Bước 5 — Kiểm tra/tạo Windows Firewall inbound rules

Các firewall rule phải cho phép TCP tới **các cổng Gateway** (8080, 8011–8014), không phải cổng sandbox 80/8080. Start script chỉ tạo SSH tunnel, không tạo Firewall rule.

Trước tiên kiểm tra rule hiện có trong PowerShell chạy quyền Administrator:

```powershell
Get-NetFirewallRule -DisplayName 'CyberRangeCZ CTF Gateway TCP *' -ErrorAction SilentlyContinue |
  Get-NetFirewallPortFilter

Get-NetFirewallRule -DisplayName 'CyberRangeCZ CTF Gateway TCP *' -ErrorAction SilentlyContinue |
  Get-NetFirewallAddressFilter
```

Đảm bảo rule là inbound/allow/TCP, local address `10.13.145.42`, local ports đúng, và remote address bằng đúng subnet/IP đã được duyệt ở Bước 2. Nếu rule thiếu hoặc scope sai, quản trị viên có thể tạo rule theo mẫu dưới đây, thay danh sách CIDR bằng giá trị xác nhận thực tế. Lệnh này làm thay đổi Firewall; chạy trong cửa sổ Administrator và chỉ sau khi phạm vi nguồn đã được duyệt:

```powershell
$clientCidrs = @('<CIDR-thí-sinh-đã-được-duyệt>')
$gatewayPorts = @(8080, 8011, 8012, 8013, 8014)

foreach ($port in $gatewayPorts) {
  New-NetFirewallRule `
    -Name "CyberRangeCZ-CTFGateway-$port" `
    -DisplayName "CyberRangeCZ CTF Gateway TCP $port" `
    -Direction Inbound -Action Allow -Protocol TCP `
    -LocalAddress '10.13.145.42' -LocalPort $port `
    -RemoteAddress $clientCidrs -Profile Any
}
```

Thay placeholder trước khi chạy. Nếu không cần ServiceDesk chung ở 8080, bỏ 8080 khỏi `$gatewayPorts`. Nếu rule cùng tên đã tồn tại, xem và cập nhật rule đó theo quy trình quản trị của trường thay vì tạo trùng. Không dùng `0.0.0.0/0` để tiện thử nếu mục tiêu là chỉ mở cho mạng trường.

### Bước 6 — Khởi chạy tunnel

Sau khi các bước preflight thành công và Firewall scope đã đúng, trong PowerShell tại thư mục gateway chạy:

```powershell
.\Start-CTFGateway.ps1
```

Script kiểm tra IP Gateway, cấu hình/alias SSH, scope đã khai báo, tính khả dụng của các cổng và backend TCP. Sau đó nó khởi chạy `ssh.exe` với một forward cho mỗi dòng `services` và theo dõi kết nối. Giữ phiên PowerShell chạy trong thời gian phục vụ. Hiện watcher thử lại tối đa 5 lần, cách nhau 5 giây; chu kỳ kiểm tra là 15 giây. Dừng có kiểm soát bằng `Ctrl+C` hoặc `.\Stop-CTFGateway.ps1`.

### Bước 7 — Kiểm tra trên Gateway

Mở một PowerShell khác và xác nhận listener chỉ ở IP Gateway:

```powershell
Get-NetTCPConnection -State Listen -LocalAddress 10.13.145.42 `
  -LocalPort 8080,8011,8012,8013,8014 |
  Select-Object LocalAddress,LocalPort,OwningProcess
```

Kiểm tra HTTP riêng từng cổng:

```powershell
curl.exe -v --max-time 10 http://10.13.145.42:8080/
curl.exe -v --max-time 10 http://10.13.145.42:8011/
curl.exe -v --max-time 10 http://10.13.145.42:8012/
curl.exe -v --max-time 10 http://10.13.145.42:8013/
curl.exe -v --max-time 10 http://10.13.145.42:8014/
```

Nếu không có listener, đọc log mới nhất trong `logs\gateway-*.log` và `logs\ssh-*.stderr.log`. Nếu có listener nhưng HTTP lỗi/treo, kiểm tra backend VM/service, vì mở listener chưa chứng minh ứng dụng xử lý HTTP thành công.

### Bước 8 — Kiểm tra từ máy thí sinh

Từ một máy khách thuộc subnet đã được phép:

```powershell
Test-NetConnection 10.13.145.42 -Port 8011
curl.exe -v --max-time 10 http://10.13.145.42:8011/
```

Sau đó thử URL tương ứng: `http://10.13.145.42:8011/` tới attacker1, 8012 tới attacker2, 8013 tới attacker3, 8014 tới attacker4; 8080 là ServiceDesk chung. Nếu `TcpTestSucceeded` là `False`, kiểm tra rule scope, route/VLAN và client isolation. Nếu TCP là `True` nhưng HTTP không trả trang, kiểm tra tunnel/backend/service trên sandbox.

### Bước 9 — Dừng hoặc thay cấu hình

Để dừng tunnel, dùng `Ctrl+C` tại cửa sổ Start hoặc chạy:

```powershell
.\Stop-CTFGateway.ps1
```

Để thêm/bỏ/đổi dịch vụ, dừng tunnel trước, sửa đúng một mục trong `services` của `config.json`, xác nhận cổng Gateway không trùng, kiểm tra JSON, cập nhật Firewall nếu cần, chạy `Test-CTFGateway.ps1 -CheckSsh`, rồi Start lại. Không sửa topology đang chạy chỉ để đổi ánh xạ gateway; đích và cổng phải là dịch vụ đã tồn tại trong sandbox.

## 3. Các địa chỉ đang được cấu hình

| URL từ máy thí sinh | Dịch vụ đích trong sandbox | Ý nghĩa |
|---|---|---|
| `http://10.13.145.42:8011` | `10.80.0.11:8080` | ServiceDesk trên attacker1 |
| `http://10.13.145.42:8012` | `10.80.0.12:8080` | ServiceDesk trên attacker2 |
| `http://10.13.145.42:8013` | `10.80.0.13:8080` | ServiceDesk trên attacker3 |
| `http://10.13.145.42:8014` | `10.80.0.14:8080` | ServiceDesk trên attacker4 |
| `http://10.13.145.42:8080` | `10.80.0.20:80` | ServiceDesk chung theo topology |

Các ánh xạ này lấy từ `config.json` trong thư mục gateway. Nếu topology hoặc cổng ứng dụng thay đổi, cần sửa đúng `sandboxIp`/`sandboxPort`/`gatewayPort` ở đó và khởi động lại tunnel. Không suy ra rằng dịch vụ đang chạy chỉ từ việc một ánh xạ đã có trong file.

## 4. Kỹ thuật SSH Local Port Forward

OpenSSH tạo một TCP listener trên Windows cho mỗi tùy chọn `-L`. Dạng tổng quát:

```text
-L <IP-bind-trên-Windows>:<cổng-máy-khách>:<IP-đích-trong-sandbox>:<cổng-đích>
```

Ví dụ ánh xạ attacker1 tương đương:

```text
-L 10.13.145.42:8011:10.80.0.11:8080
```

Khi trình duyệt gửi TCP tới `10.13.145.42:8011`, OpenSSH nhận kết nối ở Gateway, chuyển dữ liệu qua phiên SSH, rồi yêu cầu đầu bên kia SSH mở kết nối tới `10.80.0.11:8080`. Phản hồi đi ngược cùng đường hầm. Bản thân HTTP vẫn là HTTP; SSH mã hóa phần truyền giữa Gateway và đầu SSH, không tự biến URL trình duyệt thành HTTPS.

Script dùng các cờ sau:

| Cờ | Tác dụng |
|---|---|
| `-L` | Tạo local TCP port forward tới một IP/cổng đích. Script thêm một `-L` cho mỗi dịch vụ trong `config.json`. |
| `-g` | Cho phép máy khác kết nối vào local forward. Kết hợp với địa chỉ bind cụ thể `10.13.145.42`, listener được yêu cầu trên IP Gateway thay vì chỉ loopback. |
| `-N` | Không mở shell/khởi chạy lệnh từ xa; phiên SSH chỉ làm nhiệm vụ forward. |
| `-F <config>` | Dùng SSH config CyberRangeCZ đã chỉ định để lấy alias, key, ProxyJump và các tùy chọn liên quan. |
| `ExitOnForwardFailure=yes` | Báo lỗi khi SSH không tạo được listener cho forward lúc khởi động. |
| `ServerAliveInterval=30`, `ServerAliveCountMax=3` | Gửi keepalive và kết thúc phiên sau nhiều lần không nhận phản hồi, để watcher có thể thử kết nối lại. |
| `BatchMode=yes` | Không dừng chờ nhập mật khẩu tương tác; lỗi xác thực được ghi nhận thay vì treo ở prompt. |

Local forward chỉ chuyển TCP. Nó phù hợp với HTTP/HTTPS và các dịch vụ TCP khác; không chuyển UDP.

## 5. ProxyJump và vị trí của các máy sandbox

Windows không nhất thiết có route trực tiếp tới các IP riêng `10.80.0.x`. SSH config định nghĩa alias `man`, và alias này dùng `ProxyJump` để đi qua máy jump của CyberRangeCZ. Sau khi SSH thiết lập được tuyến tới MAN, MAN có thể kết nối các IP dịch vụ trong mạng sandbox.

Vì vậy đường dữ liệu có hai chặng khái niệm:

1. Windows Gateway thiết lập SSH tới alias `man` theo SSH config (qua ProxyJump nếu được cấu hình).
2. Các luồng TCP của port forward đi trong phiên SSH; phía sandbox kết nối tiếp tới IP/port đích.

`ProxyJump` là cơ chế định tuyến phiên SSH qua một máy trung gian. Nó không cài route IP sandbox lên máy thí sinh và cũng không khiến mọi IP sandbox có thể truy cập trực tiếp từ LAN.

## 6. Windows Firewall và phạm vi truy cập

SSH listener và firewall có vai trò khác nhau:

- SSH/OpenSSH tạo listener và vận chuyển dữ liệu tới đích.
- Windows Defender Firewall quyết định gói TCP từ máy khác có được phép tới listener hay không.
- Mạng trường/router/switch vẫn phải có đường mạng giữa máy thí sinh và `10.13.145.42`; firewall Windows không tạo đường định tuyến.

Cấu hình gateway hiện có `allowedClientSubnets: ["0.0.0.0/0"]`. Đây là phạm vi mọi địa chỉ IPv4, không phải subnet trường cụ thể. Nếu inbound rules hiện hành dùng cùng phạm vi, mọi nguồn IPv4 có thể định tuyến tới `10.13.145.42` đều được Windows Firewall cho phép vào các cổng đó. IP Gateway thuộc dải private nên thường không được định tuyến trực tiếp từ Internet công cộng, nhưng các mạng nội bộ có route vẫn có thể tới.

Để giới hạn chỉ máy thí sinh, quản trị viên mạng cần cung cấp chính xác CIDR hoặc danh sách IP nguồn được phép. Không thể kết luận subnet trường là `/24` chỉ từ IP `10.13.145.42`. Sau đó cập nhật `allowedClientSubnets` và phạm vi RemoteAddress của các inbound rules tương ứng. Đừng mở rule mới tới toàn bộ IPv4 nếu mục tiêu là chỉ LAN trường.

Nếu máy khách cùng mạng vẫn không vào được, nguyên nhân có thể là client isolation của Wi-Fi, ACL/VLAN, route, Windows Firewall, listener chưa chạy hoặc ứng dụng phía VM chưa phản hồi.

## 7. Các giới hạn cần hiểu

- Máy thí sinh truy cập URL Gateway, ví dụ `http://10.13.145.42:8011`; không truy cập trực tiếp `http://10.80.0.11:8080`.
- Cổng 8011–8014 là bốn cổng trên cùng một Windows Gateway, mỗi cổng được ánh xạ tới một VM/ứng dụng riêng.
- Tất cả người dùng vào cùng một cổng sẽ dùng cùng một ứng dụng đích và cùng dữ liệu mà ứng dụng đó phục vụ. SSH forward không tự tạo dữ liệu riêng theo người dùng.
- Cổng 8080 hiện trỏ ServiceDesk chung `10.80.0.20:80`; nó không phải cổng attacker1.
- Không dùng bridged networking, không bật VPN trên máy thí sinh và không cấu hình port forwarding trên router trường.
- Có firewall rule không đồng nghĩa tunnel đang chạy. Có listener không đồng nghĩa ứng dụng HTTP hoạt động tốt.
- Kiểm tra TCP chỉ xác nhận bắt tay TCP. Nó không chứng minh trang ứng dụng trả nội dung đúng hoặc xử lý được tải đồng thời.

## 8. Kiểm tra theo từng lớp

### Trên Windows Gateway

Xem listener các cổng đã cấu hình:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8011,8012,8013,8014,8080 |
  Select-Object LocalAddress,LocalPort,OwningProcess
```

Xem TCP/HTTP từ chính Gateway:

```powershell
Test-NetConnection 10.13.145.42 -Port 8011
curl.exe -v --max-time 10 http://10.13.145.42:8011/
```

Thử lặp lại cho từng cổng. `TcpTestSucceeded: True` là kiểm tra TCP; `curl` mới cho biết có phản hồi HTTP hay không. Mã HTTP 4xx/5xx vẫn chứng minh đã có phản hồi HTTP nhưng ứng dụng có thể báo lỗi.

### Từ máy thí sinh

```powershell
Test-NetConnection 10.13.145.42 -Port 8011
curl.exe -v --max-time 10 http://10.13.145.42:8011/
```

Diễn giải nhanh:

| Kết quả | Kiểm tra tiếp |
|---|---|
| Gateway không có listener | Tunnel chưa chạy, bind sai IP/cổng, hoặc SSH khởi động lỗi. Xem log gateway/SSH. |
| Gateway truy cập được, máy thí sinh timeout | RemoteAddress của firewall, VLAN/route, Wi-Fi client isolation hoặc ACL mạng. |
| TCP thành công nhưng `curl` treo/lỗi | SSH forward có thể hoạt động nhưng backend không phản hồi hoặc ứng dụng bị quá tải. Kiểm tra log và ứng dụng trên VM qua quy trình quản trị sandbox. |
| Trình duyệt hiện trang nhưng login không phù hợp | Kiểm tra cấu hình ứng dụng và dữ liệu của đúng đội; cổng forward không thay đổi tài khoản hay dữ liệu. |

`Test-CTFGateway.ps1` có thể kiểm tra cấu hình/listener và tùy chọn `-CheckSsh` dùng forward kiểm tra chỉ bind loopback. Các log trong `logs` hỗ trợ tìm lỗi SSH. Kiểm tra sức khỏe hiện tại chủ yếu là TCP; nó không đo thời gian phản hồi HTTP hay tải ứng dụng.

## 9. Chạy và dừng tunnel

Mở PowerShell tại thư mục `CyberRangeCZ-Windows-Gateway`:

```powershell
.\Test-CTFGateway.ps1
.\Start-CTFGateway.ps1
```

Start chạy tiến trình SSH được script quản lý và theo dõi trạng thái; để tunnel phục vụ thì cửa sổ/script phải tiếp tục chạy. Script thử kết nối lại theo giới hạn `maxRestartAttempts` trong `config.json` (hiện là 5 lần, cách nhau 5 giây). Dừng bằng `Ctrl+C` hoặc:

```powershell
.\Stop-CTFGateway.ps1
```

Stop nhắm tới tiến trình SSH mà gateway script đã ghi nhận, không nên dừng phiên SSH khác. Các firewall rules là cấu hình Windows riêng; Start/Stop tunnel không đồng nghĩa tạo/xóa rule firewall.

## 10. Host key, SSH config và bí mật

SSH host key fingerprint giúp xác định đúng máy SSH ở đầu kết nối, tránh chấp nhận nhầm host. Script dùng cấu hình runtime/known_hosts riêng và chính sách xác minh host key; khi pool hoặc host thay đổi, cần xác minh fingerprint mới qua kênh quản trị CyberRangeCZ trước khi chấp nhận. Không khắc phục lỗi bằng `StrictHostKeyChecking=no`.

Private key, mật khẩu dịch vụ và dữ liệu xác thực không nên ghi vào tài liệu, log công khai, Git hoặc gửi cho thí sinh. Chỉ Windows Gateway cần private key để tạo tunnel. Khi báo lỗi, chia sẻ thông báo lỗi và fingerprint nếu cần, nhưng không chia sẻ nội dung private key.

## 11. Tóm tắt vai trò các thành phần

```text
Firewall     = cho/không cho máy LAN vào cổng Windows
SSH -L       = ánh xạ cổng Windows tới IP:port dịch vụ sandbox
-g + bind IP = cho máy khác dùng listener trên IP Gateway
ProxyJump    = đưa phiên SSH tới mạng CyberRangeCZ qua máy trung gian
OpenSSH key  = xác thực Gateway với CyberRangeCZ; không cấp cho thí sinh
LAN routing  = đưa gói từ máy thí sinh tới IP Gateway; do hạ tầng mạng quyết định
Ứng dụng VM  = xử lý HTTP, tài khoản, dữ liệu và tải đồng thời
```

Tóm lại, người dùng LAN mở kết nối tới một cổng trên Windows Gateway. Windows Firewall cho phép kết nối đó; OpenSSH nhận TCP và chuyển nó qua SSH/ProxyJump tới cổng của dịch vụ trong sandbox; câu trả lời quay ngược về trình duyệt qua tunnel. Mỗi lớp phải hoạt động thì dịch vụ mới dùng được.
