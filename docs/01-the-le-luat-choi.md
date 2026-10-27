# Thể lệ và luật chơi cuộc thi Attack–Defense

*Tài liệu lý thuyết – phục vụ thiết kế cuộc thi tuyển chọn sinh viên An toàn thông tin.*

## 1. Mục tiêu cuộc thi

Cuộc thi Attack–Defense (A–D) nhằm **quan sát đồng thời ba năng lực** của người chơi trên cùng một hệ thống:

- **Tấn công (Attack):** phát hiện và khai thác lỗ hổng trên service của đội đối thủ để lấy flag.
- **Phòng thủ (Defense):** phát hiện lỗ hổng trên service của chính đội, vá lỗi và chống lại khai thác của đối thủ.
- **Duy trì dịch vụ (SLA):** giữ cho service luôn hoạt động đúng chức năng trong lúc vừa bị tấn công vừa phải vá.

Vì mục tiêu là **tuyển chọn**, điểm được tách thành ba thành phần độc lập (Attack, Defense, SLA) để sau cuộc thi có thể nhận ra ứng viên mạnh về khai thác, mạnh về phòng thủ hay mạnh về vận hành hệ thống.

## 2. Số đội và mô hình thi

- **Thiết kế tổng quát:** tới 4 đội (A, B, C, D), mỗi đội một bản service giống hệt nhau lúc khởi đầu.
- **Phạm vi mô phỏng/báo cáo:** 2 đội (A và B) để trình bày trọn vẹn một ván đấu.
- Mỗi đội có **toàn quyền trên môi trường của mình** để phòng thủ, đồng thời được phép truy cập cổng dịch vụ của các đội còn lại qua *mạng thi đấu* (Game Network) để tấn công.
- Các thành phần điều khiển (Game Controller, Checker, Flag Generator, Scoreboard) nằm trong *mạng điều khiển* (Control Network) riêng, **không thuộc phạm vi tấn công** của thí sinh.

## 3. Đơn vị thời gian: tick và vòng

Cuộc thi được chia thành các **tick** (nhịp) liên tiếp, độ dài cố định (ví dụ 60–120 giây). Trong mỗi tick:

1. Hệ thống **xoay flag mới** cho từng service của từng đội.
2. **Checker** kiểm tra mọi service (còn sống không, chức năng hợp lệ không, flag đặt/đọc được không).
3. Điểm **Attack / Defense / SLA** của tick được chốt theo các giá trị quan sát được.

Nhiều tick gộp thành một **vòng (phase)**. Mỗi vòng có cấu hình luật khác nhau nhằm dẫn dắt hành vi người chơi theo từng giai đoạn.

## 4. Ba vòng thi và lý do khác nhau

| Vòng | Tên | Nội dung | Luật đặc thù | Vì sao có vòng này |
| --- | --- | --- | --- | --- |
| **Vòng 1** | Củng cố | Chỉ **Defense + SLA** được tính; Attack chưa cộng điểm. Các đội tập trung đọc mã, tìm lỗ hổng trên service của mình, vá và giữ service sống. | Attack = 0 (không ghi điểm tấn công). | Cho đội thời gian hiểu service và dựng thế phòng thủ trước khi va chạm, tránh việc một exploit sớm quyết định toàn bộ kết quả. |
| **Vòng 2** | Attack–Defense đầy đủ | Tính **cả ba** thành phần theo công thức chuẩn. Đây là phần chính của cuộc thi. | Hệ số ×1. | Đánh giá cân bằng cả tấn công, phòng thủ và duy trì dịch vụ trong điều kiện đối kháng thật. |
| **Vòng 3** | Tăng tốc | Tick ngắn hơn, **hệ số điểm cao hơn** (ví dụ ×2) cho Attack và Defense. | Tick rút ngắn, nhân hệ số. | Tạo bứt phá cuối, thưởng cho đội duy trì phong độ và tránh hòa; phân hóa thứ hạng rõ ở chặng cuối. |

> Việc chia vòng không đổi *bản chất* công thức chấm điểm, chỉ đổi **điều kiện áp dụng** (bật/tắt Attack, hệ số, độ dài tick). Nhờ đó cuộc thi có nhịp độ và tính sư phạm rõ ràng.

## 5. Luật nộp flag

- Flag có định dạng cố định, ví dụ `FLAG{<đội_bị_tấn_công>_<tick>_<ngẫu_nhiên>}`, **mỗi tick một giá trị mới**.
- Đội tấn công khai thác service đối thủ, lấy flag rồi **nộp lên Game Server** qua cổng nộp flag.
- Một lần nộp được tính điểm Attack **chỉ khi** flag: (a) hợp lệ, (b) còn đúng tick hiện tại, (c) thuộc service của **đội khác**, không phải của chính mình.
- **Nộp lại cùng một flag** không được cộng điểm thêm.
- Flag hết hạn, flag của chính đội, hoặc flag không tồn tại: **không tính điểm**.

## 6. Cách tính điểm

Điểm tổng của một đội là tổng ba thành phần trên toàn bộ cuộc thi:

```
Total = Σ Attack + Σ Defense + Σ SLA
```

Phép **cộng** (thay vì nhân) được chọn để một đội yếu ở một khía cạnh không mất sạch điểm ở các khía cạnh khác, và để tách được ba chỉ số năng lực phục vụ tuyển chọn (Zafar et al., 2024, Sec. 7.2.4).

### 6.1. Điểm Attack (mỗi flag hợp lệ)

```
Attack = 1 + 1/C_f + R(A,V)          (tối đa 3 điểm/flag)
```

- **Base = 1:** mọi exploit thành công đều có giá trị.
- **Dynamic = 1/C_f:** `C_f` là số đội cùng capture được flag đó trong tick. Flag càng ít đội lấy được càng khó, điểm càng cao (1 đội → 1; 2 đội → 0,5; 5 đội → 0,2).
- **Rank = R(A,V):** điều chỉnh theo tương quan thứ hạng attacker A và victim V đầu tick:

```
R(A,V) = 1                                              nếu pos_A ≥ pos_V
R(A,V) = (1/500) × [30 + 470 / (1 + ((pos_V − pos_A)/11.92)^1.2)]   nếu pos_A < pos_V
```

(pos = thứ hạng, số nhỏ = hạng cao.) Đội yếu đánh thắng đội mạnh nhận trọn 1 điểm rank; đội mạnh đánh đội yếu bị giảm theo hàm decay. Các hằng số `30, 470, 500, 11.92, 1.2` kế thừa dạng hàm 34C3 CTF (giảm ổn định, không phụ thuộc số đội).

### 6.2. Điểm Defense (mỗi service, mỗi tick)

```
Defense = (2 + 1/N_D) × I_UP          (tối đa 3 điểm)
```

- `N_D` = số đội cùng bảo vệ thành công service cùng loại trong tick.
- `I_UP = 1` nếu service hoạt động đúng, `0` nếu service chết.
- Base = 2 để phòng thủ vẫn đáng giá kể cả khi nhiều đội cùng vá được.
- Nhân `I_UP` để **ngăn chiến thuật tắt service**: service chết thì Defense = 0 dù không mất flag.

### 6.3. Điểm SLA (mỗi service, mỗi tick)

```
SLA = 3 × I_UP
```

Service chỉ được coi là "UP" khi **checker xác nhận chức năng hợp lệ** (đăng nhập, đọc/ghi dữ liệu, lưu/đọc flag), không chỉ mở port. Patch làm hỏng chức năng hợp lệ ⇒ mất SLA. Mức 3 bằng mức tối đa của một Attack để cân bằng động lực.

### 6.4. Quan hệ Defense – SLA

| Tình huống | SLA | Defense |
| --- | --- | --- |
| Service UP, flag **không** bị lấy | 3 | 2 + 1/N_D |
| Service UP, flag **bị** lấy | 3 | 0 |
| Service DOWN | 0 | 0 |

## 7. Điều kiện chiến thắng

- Kết thúc cuộc thi, đội có **Total** cao nhất thắng.
- Trường hợp cần tách: xét lần lượt Σ Attack → Σ Defense → Σ SLA, hoặc theo tiêu chí ban tổ chức công bố trước.
- Nhờ tách ba thành phần, ngoài đội vô địch còn xác định được "mạnh tấn công", "mạnh phòng thủ", "mạnh vận hành" phục vụ tuyển chọn.

## 8. Quy tắc triển khai (chốt để nhất quán)

1. Flag chỉ tính Attack khi hợp lệ, đúng tick, thuộc service đối thủ.
2. Nộp lại cùng flag không cộng thêm.
3. `C_f` chốt ở cuối tick để các đội capture cùng flag được đánh giá cùng mức khó.
4. `N_D` xác định ở cuối tick theo số đội có service UP và không bị mất flag.
5. Rank của attacker/victim lấy ở **đầu tick** để không đổi công thức giữa chừng.
6. Checker phải kiểm tra **chức năng hợp lệ**, không chỉ port/kết nối.

## Tài liệu tham khảo

[1] A. Zafar, M. M. Yamin, B. Katt, E. Torseth, "All flags are not created equal: A deep look into CTF Scoring Algorithms," *Expert Systems with Applications*, vol. 254, 2024, 124436.
