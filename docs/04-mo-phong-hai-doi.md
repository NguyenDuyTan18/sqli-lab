# Mô phỏng hai đội thi đấu (ván mẫu trên giấy)

*Tài liệu lý thuyết – diễn giải từng bước một ván 2 đội, từ khởi đầu đến xác định đội thắng.*

## 1. Thiết lập

- Hai đội **A** và **B**, mỗi đội một service **ServiceDesk** (cùng loại service).
- Ván mẫu diễn ra trong **Vòng 2 (Attack–Defense đầy đủ)**, hệ số ×1, gồm **4 tick**.
- Ban đầu cả hai service đều ở cấu hình **vulnerable** (còn lỗi IDOR), đều **UP**.
- Để số học rõ ràng, giả định thứ hạng hai đội **ngang nhau ở đầu mỗi tick** nên `pos_A ≥ pos_V` luôn đúng ⇒ `R(A,V) = 1`. (Trường hợp thực tế R thay đổi theo chênh lệch hạng.)
- Mỗi flag trong ván này chỉ bị **1 đội** capture ⇒ `C_f = 1` ⇒ phần động `1/C_f = 1`.

Nhắc lại công thức:
`Attack = 1 + 1/C_f + R(A,V)` · `Defense = (2 + 1/N_D) × I_UP` · `SLA = 3 × I_UP`.

## 2. Diễn tiến từng tick

### Tick 1 — Va chạm đầu tiên (cả hai còn lỗi)

1. Hệ thống đặt flag mới cho A và B.
2. **A khai thác IDOR của B**: dò id, đọc ticket mật của B, lấy `FLAG{B_T1_...}`, nộp lên Game Server → hợp lệ.
3. **B khai thác IDOR của A** tương tự, lấy `FLAG{A_T1_...}`, nộp → hợp lệ.
4. Checker xác nhận cả hai service vẫn UP và chức năng hợp lệ.

Chốt tick 1:

| Đội | Attack | Defense | SLA | Điểm tick |
| --- | --- | --- | --- | --- |
| A | 1+1+1 = **3** | flag bị lấy ⇒ **0** | UP ⇒ **3** | **6** |
| B | 1+1+1 = **3** | flag bị lấy ⇒ **0** | UP ⇒ **3** | **6** |

Tổng tích lũy: **A = 6, B = 6** (hòa).

### Tick 2 — B vá trước

1. B nhận ra lỗi, thêm kiểm tra chủ sở hữu, chuyển service sang **patched**, giữ chức năng ⇒ vẫn UP.
2. **A tấn công B → thất bại** (403, không đọc được ticket mật của B).
3. A chưa vá ⇒ **B tấn công A thành công**, lấy `FLAG{A_T2_...}`, nộp → hợp lệ.
4. Checker: cả hai UP; flag của B **không** bị lấy, flag của A **bị** lấy.

`N_D` (số đội phòng thủ thành công service này) = 1 (chỉ B).

Chốt tick 2:

| Đội | Attack | Defense | SLA | Điểm tick |
| --- | --- | --- | --- | --- |
| A | không lấy được flag ⇒ **0** | flag bị lấy ⇒ **0** | UP ⇒ **3** | **3** |
| B | 1+1+1 = **3** | (2 + 1/1)×1 = **3** | UP ⇒ **3** | **9** |

Tổng tích lũy: **A = 9, B = 15** → B vươn lên dẫn đầu nhờ **vá trước**.

### Tick 3 — A cũng vá, thế cân bằng

1. A vá thành công, giữ chức năng ⇒ UP.
2. Cả hai patched ⇒ **không đội nào lấy được flag** của đối thủ.
3. Checker: cả hai UP, không mất flag.

`N_D` = 2 (cả A và B phòng thủ thành công) ⇒ Defense = 2 + 1/2 = **2,5**.

Chốt tick 3:

| Đội | Attack | Defense | SLA | Điểm tick |
| --- | --- | --- | --- | --- |
| A | **0** | (2 + 1/2)×1 = **2,5** | UP ⇒ **3** | **5,5** |
| B | **0** | (2 + 1/2)×1 = **2,5** | UP ⇒ **3** | **5,5** |

Tổng tích lũy: **A = 14,5, B = 20,5**.

### Tick 4 — A vá hỏng chức năng (service DOWN)

1. Bản vá của A vô tình làm hỏng chức năng đăng nhập ⇒ **checker báo A DOWN** (`I_UP = 0`).
2. B vẫn patched và UP.
3. A DOWN nên không ai lấy được flag của A; B không có mục tiêu khai thác.

`N_D` = 1 (chỉ B phòng thủ thành công; A down không được tính).

Chốt tick 4:

| Đội | Attack | Defense | SLA | Điểm tick |
| --- | --- | --- | --- | --- |
| A | **0** | DOWN ⇒ **0** | DOWN ⇒ **0** | **0** |
| B | **0** | (2 + 1/1)×1 = **3** | UP ⇒ **3** | **6** |

Tổng tích lũy: **A = 14,5, B = 26,5**.

## 3. Kết quả và đội thắng

| Đội | Σ Attack | Σ Defense | Σ SLA | **Total** |
| --- | --- | --- | --- | --- |
| A | 3 | 0 + 0 + 2,5 + 0 = 2,5 | 3 + 3 + 3 + 0 = 9 | **14,5** |
| B | 3 + 3 = 6 | 0 + 3 + 2,5 + 3 = 8,5 | 3 + 3 + 3 + 3 = 12 | **26,5** |

**Đội B thắng** với 26,5 điểm so với 14,5 của A.

## 4. Bài học rút ra từ ván mẫu (ý nghĩa sư phạm)

- **Vá sớm thắng lớn:** B vượt lên ngay tick 2 nhờ vá trước và giữ service sống.
- **Vá phải an toàn:** tick 4 cho thấy bản vá làm hỏng chức năng khiến A mất cả Defense lẫn SLA — tệ hơn cả khi còn lỗi.
- **Không được tắt service:** mọi tình huống DOWN đều về 0 điểm, đúng tinh thần A–D.
- **Ba năng lực tách bạch:** nhìn cột Σ Attack / Σ Defense / Σ SLA có thể đánh giá riêng từng khả năng của mỗi đội phục vụ tuyển chọn.
