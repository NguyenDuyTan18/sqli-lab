# Bộ tài liệu lý thuyết cuộc thi Attack–Defense (ServiceDesk IDOR)

Tài liệu thiết kế cuộc thi Attack–Defense phục vụ tuyển chọn sinh viên, viết ở dạng thuần lý thuyết. Dùng lại challenge **ServiceDesk IDOR** của dự án và cơ chế chấm điểm theo Zafar et al. (2024).

| # | Tài liệu | Nội dung | Góp ý đáp ứng |
| --- | --- | --- | --- |
| 1 | [Thể lệ và luật chơi](01-the-le-luat-choi.md) | Số đội, 3 vòng và lý do khác nhau, mục tiêu, luật nộp flag, cách tính điểm Attack/Defense/SLA, điều kiện thắng. | #1 |
| 2 | [Mô hình cuộc thi](02-mo-hinh-cuoc-thi.md) | Các thực thể (Team, Phase, Tick, Challenge, Service, Flag, Capture, CheckResult, Score) và quan hệ; sơ đồ ER. | #2 |
| 3 | [Kịch bản IDOR](03-kich-ban-idor.md) | Challenge ServiceDesk, môi trường, vị trí flag, cách tấn công, phòng thủ, điều kiện thắng. | #3 |
| 4 | [Mô phỏng hai đội](04-mo-phong-hai-doi.md) | Ván mẫu 2 đội qua 4 tick: khai thác → lấy flag → kiểm tra → tính điểm → xác định đội thắng. | #4 |
| 5 | [Sơ đồ](05-so-do.md) | Sơ đồ mô hình hệ thống và sơ đồ tuần tự (Sequence Diagram) một tick. | #5 |
| 6 | [Vai trò hệ thống](06-vai-tro-he-thong.md) | Phân biệt BTC chuẩn bị / hệ thống tự động / thí sinh thao tác; ranh giới chống gian lận. | #6 |

> Góp ý #7 (ưu tiên phần cốt lõi) được phản ánh ở tài liệu 1 (chia vòng) và 6 (xác định đâu là phần hệ thống tự động cần dựng chạy trước).

## Sản phẩm cho buổi báo cáo tiếp theo

- **Thể lệ & luật chơi:** tài liệu 1.
- **Kịch bản hoàn chỉnh 2 đội:** tài liệu 3 + 4.
- **Sơ đồ mô hình hệ thống & sơ đồ tuần tự:** tài liệu 2 (ER) + 5 (hệ thống, tuần tự).
- **Mô phỏng tấn công–phòng thủ–tính điểm:** tài liệu 4.

## Xuất ra .docx

Sơ đồ viết bằng Mermaid. Xem [cách xuất .docx](EXPORT.md) để render sơ đồ ra ảnh và gộp các tài liệu thành một file Word.
