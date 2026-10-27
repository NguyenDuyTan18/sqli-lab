# Sửa lỗi topology có OS type bằng null

Console đã ghi nhận:

```text
ZodError: Expected 'linux' | 'windows', received null
```

Frontend gặp giá trị `os_type: null` khi đọc dữ liệu topology. Backend lấy
giá trị này từ image OpenStack. Vì vậy máy ảo có thể tạo và provisioning
thành công nhưng portal vẫn không tải được sơ đồ.

## Sandbox đang chạy với Ubuntu 22.04

Trên máy có OpenStack CLI đã xác thực đúng cloud/project, xem metadata image:

```bash
openstack image show ubuntu-22.04 -c id -c name -c properties -f yaml
openstack image show debian-12-x86_64 -c id -c name -c properties -f yaml
```

Nếu Ubuntu thiếu `os_type`, người có quyền sửa image chạy:

```bash
openstack image set --property os_type=linux ubuntu-22.04
openstack image show ubuntu-22.04 -c id -c name -c properties -f yaml
```

Nếu có nhiều image trùng tên, dùng đúng ID của image đã cấp phát cho sandbox
thay cho tên. Kiểm tra cả image của router; chỉ sửa image Linux bị thiếu hoặc
có giá trị `os_type` sai. Nếu image Debian cũng thiếu, đặt `os_type=linux`
cho đúng image Debian đó.

Tải lại topology của sandbox hiện tại. Trong Network, Response của request
`/sandboxes/<uuid>/topology` phải có `os_type: "linux"` cho các máy Linux.
Nếu Response vẫn là null sau khi metadata đã đúng, quản trị viên cần kiểm tra
cache image/topology hoặc việc backend truy cập đúng cloud/project. Việc sửa
metadata này cần được xác nhận trên cloud; thay source không cập nhật image
trên OpenStack.

## Cấp phát sandbox mới từ source này

Topology mặc định đã chuyển cả bốn máy đội và checker sang
`debian-12-x86_64`, tài khoản quản lý `debian`. Router dùng cùng image.
Image này được chọn theo bài mẫu; trước khi cấp phát, xác nhận metadata của
image trên cloud thực tế có `os_type=linux`.

Đưa nội dung thư mục lab vào gốc Git repo, chọn revision đã cập nhật và cấp
phát sandbox mới. Chỉ chạy lại provisioning trên sandbox cũ sẽ không thay
image hệ điều hành của các máy đã tạo.

`os_type` là metadata image, không thêm thuộc tính này vào `base_box` trong
`topology.yml`. IP đội, dịch vụ SQLi và cơ chế controller qua SSH dùng cấu hình
hiện có; dùng gói management SSH access của sandbox mới khi chuyển sandbox.

Tham khảo:

- [Backend lấy OS type từ image](https://github.com/cyberrangecz/backend-sandbox-service/blob/master/crczp/sandbox_instance_app/lib/topology.py)
- [OpenStack image commands](https://docs.openstack.org/python-openstackclient/latest/cli/command-objects/image/v2/index.html)
