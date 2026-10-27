# Phân vai trong hệ thống Attack–Defense

*Tài liệu lý thuyết – phân biệt rõ ba nhóm vai trò: ban tổ chức chuẩn bị, hệ thống tự động, và thí sinh thao tác.*

## 1. Vì sao cần phân vai rõ

Trong A–D dễ nhầm lẫn "ai làm gì": việc nào do con người ban tổ chức (BTC) chuẩn bị trước, việc nào hệ thống tự chạy khi thi, việc nào do thí sinh. Phân vai rõ giúp thiết kế đúng, chấm điểm minh bạch và tránh gian lận.

## 2. Ban tổ chức chuẩn bị (trước cuộc thi, làm một lần)

- Xây dựng **challenge** ServiceDesk có lỗi IDOR và bản tham chiếu đã vá.
- Thiết lập **topology**: service mỗi đội trong Game Network; Game Controller/Checker/Flag Generator/Scoreboard/Submission trong Control Network.
- Cấu hình **mạng & phân quyền**: đội truy cập được service đối thủ và cổng nộp flag; không truy cập được vùng điều khiển.
- Khởi tạo **tài khoản đội**, phát **token nộp flag** cho từng đội và **token quản trị (checker)** giữ bí mật.
- Định nghĩa **thể lệ**: số đội, số vòng, luật từng vòng, công thức điểm, tiêu chí thắng.
- Nạp **cấu hình vòng/tick**: độ dài tick, hệ số, bật/tắt Attack theo vòng.

## 3. Hệ thống tự động thực hiện (trong khi thi, lặp mỗi tick)

| Thành phần | Việc tự động làm |
| --- | --- |
| **Game Controller** | Chạy vòng lặp tick, chuyển vòng, chốt thứ hạng đầu tick. |
| **Flag Generator** | Sinh và **xoay flag** mới cho mọi service mỗi tick qua kênh quản trị. |
| **Checker** | Mỗi tick kiểm tra **chức năng hợp lệ** của từng service (đăng nhập/đọc/ghi/đọc lại flag) ⇒ xác định `I_UP` cho SLA. |
| **Submission API** | Nhận flag đội nộp, kiểm tra hợp lệ (đúng tick, đúng victim, không trùng). |
| **Scoring Engine** | Cuối tick tính `C_f`, `N_D` rồi ra Attack/Defense/SLA và tổng. |
| **Scoreboard** | Hiển thị điểm và trạng thái service theo tick. |

> Những việc này **không cần con người** can thiệp trong lúc thi — đó là phần "cốt lõi" cần ưu tiên dựng chạy được trước.

## 4. Thí sinh thao tác (trong khi thi)

- **Tấn công:** phân tích service đối thủ, khai thác IDOR, lấy flag và **nộp** lên Submission API.
- **Phòng thủ:** đọc mã/log service của mình, tìm lỗ hổng, **vá** (thêm kiểm tra phân quyền) và chuyển service sang cấu hình đã vá.
- **Duy trì SLA:** đảm bảo sau khi vá, chức năng hợp lệ vẫn chạy để checker báo UP; **không được tắt service** để né tấn công.
- Thí sinh **không** sinh flag, **không** chạm vùng điều khiển, **không** tự chấm điểm.

## 5. Bảng phân vai tổng hợp

| Hoạt động | BTC chuẩn bị | Hệ thống tự động | Thí sinh |
| --- | :---: | :---: | :---: |
| Tạo challenge & bản vá tham chiếu | ✓ | | |
| Dựng topology & mạng | ✓ | | |
| Phát token đội / token quản trị | ✓ | | |
| Sinh & xoay flag mỗi tick | | ✓ | |
| Kiểm tra SLA (checker) | | ✓ | |
| Nhận & kiểm tra flag nộp | | ✓ | |
| Tính điểm & cập nhật scoreboard | | ✓ | |
| Khai thác service đối thủ, nộp flag | | | ✓ |
| Vá lỗ hổng, giữ service sống | | | ✓ |

## 6. Ranh giới chống gian lận

- Thí sinh không có token quản trị nên **không thể tự ghi đè flag** của mình để tránh mất điểm.
- Flag xoay theo tick ⇒ **không thể để dành** flag cũ nộp sau.
- Scoring chốt `C_f`, `N_D` ở cuối tick và rank ở đầu tick ⇒ công thức **ổn định**, không bị tác động giữa chừng.
- Vùng điều khiển tách khỏi vùng thi ⇒ hạ tầng chấm điểm **ngoài tầm tấn công**.
