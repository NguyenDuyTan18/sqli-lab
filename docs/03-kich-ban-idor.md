# Kịch bản Attack–Defense: ServiceDesk – IDOR (CWE-639)

*Tài liệu lý thuyết – một kịch bản cụ thể để thí sinh tấn công, phòng thủ và chấm điểm.*

## 1. Chọn challenge và lý do

Challenge là **ServiceDesk** – một cổng quản lý ticket hỗ trợ nội bộ, cố ý chứa lỗi **IDOR (Insecure Direct Object Reference / Broken Object Level Authorization)**, phân loại **CWE-639 – Authorization Bypass Through User-Controlled Key**.

IDOR phù hợp cho mô hình A–D vì nó kiểm tra đồng thời:

- **Tấn công:** nhận ra endpoint tham chiếu trực tiếp theo id và thử truy cập tài nguyên không thuộc về mình.
- **Phòng thủ:** thêm kiểm tra phân quyền ở tầng đối tượng mà **không phá vỡ** chức năng hợp lệ.
- **Duy trì (SLA):** sau khi vá, các chức năng đăng nhập/đọc/ghi ticket vẫn phải chạy đúng để checker xác nhận UP.

## 2. Năng lực được đánh giá (ánh xạ khung)

| Khung | Thành phần | Năng lực được đánh giá |
| --- | --- | --- |
| CWE | CWE-639 (IDOR) | Nhận diện và khắc phục lỗi phân quyền theo khóa do người dùng kiểm soát. |
| MITRE ATT&CK | T1190 – Exploit Public-Facing Application | Khai thác dịch vụ web công bố trong Game Network. |
| MITRE ATT&CK | T1083 / T1005 – Discovery & Data from Local System | Dò id tài nguyên và đọc dữ liệu mật (flag). |
| NICE | Vulnerability Analysis / Incident Response | Phân tích log, xác định thời điểm bị khai thác, vá và kiểm chứng. |

## 3. Đặc tả dịch vụ ServiceDesk

- Ứng dụng web nhỏ (HTTP) cung cấp: đăng nhập, xem danh sách ticket **của mình**, xem chi tiết một ticket theo id, cập nhật trạng thái ticket.
- Mỗi ticket gồm: `id`, `owner`, `title`, `status`, `private_note` (ghi chú mật).
- Dữ liệu khởi tạo có một **ticket mật** của một chủ sở hữu đặc biệt (ví dụ `carol`), trong đó trường `private_note` chính là **nơi chứa flag** của tick hiện tại.
- Service có hai cấu hình:
  - **Vulnerable (ban đầu):** endpoint xem chi tiết ticket `GET /api/tickets/<id>` **không kiểm tra** ticket có thuộc về người gọi hay không ⇒ bất kỳ phiên hợp lệ nào (kể cả tài khoản khách mặc định đi kèm service) cũng đọc được ticket của người khác bằng cách đổi `<id>`.
  - **Patched (sau khi đội vá):** endpoint kiểm tra `ticket.owner == người_dùng_hiện_tại`, trả `403 Forbidden` nếu không phải chủ sở hữu ⇒ flag không còn đọc được từ ngoài.

## 4. Vị trí flag và cách xoay flag

- Flag của mỗi đội nằm trong `private_note` của **ticket mật** trên service của đội đó.
- **Mỗi tick**, hệ thống (Checker/Flag Generator) đặt một flag mới vào ticket mật thông qua một **kênh quản trị riêng** mà chỉ ban tổ chức có khóa (token-checker). Thí sinh **không** có khóa này, nên không thể tự ghi đè flag để gian lận.
- Flag cũ hết hiệu lực ngay khi tick mới bắt đầu ⇒ không thể "để dành" flag nộp ở tick sau.

> Ví dụ: ở tick 15, service của Team B chứa `FLAG{TEAM_B_T15_d19e83}`. Sang tick 16, giá trị này bị thay và không còn được tính điểm.

## 5. Cách tấn công (phía attacker)

1. Mở service của đội đối thủ trong Game Network (ví dụ Team A nhắm service của Team B).
2. Dùng tài khoản khách/phiên hợp lệ của chính mình trên service đối thủ (service ship sẵn), truy cập `GET /api/tickets/<id>` rồi **dò id** của ticket mật.
3. Do thiếu kiểm tra phân quyền (IDOR), server trả về **toàn bộ** ticket mật, lộ `private_note` chứa flag.
4. Trích flag và **nộp lên Game Server** qua cổng nộp flag.

## 6. Cách phòng thủ (phía victim)

1. Đọc mã/log, nhận ra `GET /api/tickets/<id>` thiếu kiểm tra chủ sở hữu.
2. **Vá:** thêm điều kiện `ticket.owner == current_user` (trả 403 nếu sai) cho cả thao tác đọc và cập nhật; chuyển service sang cấu hình *patched* rồi khởi động lại.
3. Đảm bảo chức năng hợp lệ vẫn nguyên vẹn: người dùng vẫn đăng nhập, xem ticket của mình, cập nhật trạng thái — để checker xác nhận **SLA UP**.

> Lưu ý phản mẫu: **tắt service** để "khỏi bị lấy flag" sẽ khiến `I_UP = 0` ⇒ mất cả Defense lẫn SLA (0 điểm). Phòng thủ đúng là *vá mà vẫn sống*.

## 7. Điều kiện chiến thắng của kịch bản

Trong một tick, với mỗi service:

| Quan sát | Kết quả điểm |
| --- | --- |
| Đội tấn công lấy & nộp được flag đối thủ (hợp lệ, đúng tick) | Attacker +Attack; victim mất Defense tick đó |
| Service của đội UP và flag **không** bị lấy | Đội +Defense và +SLA |
| Service UP nhưng flag bị lấy | +SLA, Defense = 0 |
| Service DOWN | Defense = SLA = 0 |

Tích lũy qua toàn bộ tick/vòng, đội có `Total = ΣAttack + ΣDefense + ΣSLA` cao nhất là đội thắng. Chi tiết ván mô phỏng xem tài liệu *Mô phỏng hai đội*.
