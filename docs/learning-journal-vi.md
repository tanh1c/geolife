# Learning Journal — VI

## 2026-09-16 — Vì sao GeoLife cần EDA sâu hơn

GeoLife không phải dataset tabular i.i.d. đơn giản. Dữ liệu có cấu trúc phân cấp và spatiotemporal: point thuộc trajectory, trajectory thuộc user; mỗi user có độ dài lịch sử rất khác nhau; sampling rate thay đổi; và geography/timezone ảnh hưởng trực tiếp tới cách diễn giải hành vi.

Điểm học được:

- phải verify số lượng từ file thật thay vì tin hoàn toàn vào documentation;
- xem distribution raw trước khi chọn cleaning threshold;
- không cần nhét toàn bộ GPS point vào một DataFrame lớn nếu có thể reduce theo trajectory;
- phải phân tích imbalance theo user vì Home/Office cần hành vi lặp lại theo thời gian;
- transportation labels chỉ là nhãn chuyển động phụ trợ, không phải ground truth Home/Office;
- phải chốt timezone semantics trước khi dùng rule như `night = Home` hay `office hours = Office`;
- privacy của mobility data là vấn đề thiết kế hệ thống, không chỉ là phần viết báo cáo.

## 2026-09-16 — Distribution thực tế đã thay đổi cách nhìn thế nào

Release đang mount có 182 users và 18,670 trajectory files. Distribution theo user rất long-tailed: median chỉ 27.5 trajectories/user nhưng user lớn nhất có 2,153 trajectories. Chỉ top 10 users đã đóng góp 47.4% toàn bộ trajectories.

Điều này ảnh hưởng trực tiếp tới evaluation. Nếu chỉ tính một metric weighted theo từng trajectory/observation thì kết quả có thể bị chi phối bởi heavy users. Vì vậy về sau nên cân nhắc thêm per-user/macro evaluation bên cạnh micro/observation-level metrics.

Nhóm user có transportation-label file chỉ là 69/182 users nhưng chiếm 58.4% trajectories. Do đó labeled subset không đại diện ngẫu nhiên cho toàn bộ dataset theo trajectory volume.

Raw trajectory spot-check cũng cho thấy một bài học DS quan trọng: timestamp parse sạch sang UTC nhưng altitude có range rất rộng. Không nên thấy một giá trị lạ rồi biến ngay thành cleaning rule; cần nhìn distribution toàn dataset trước.

## 2026-09-16 — Data-quality diagnostics làm thay đổi kế hoạch cleaning

Full scan xác nhận 24,876,978 GPS points. Kết quả cũng cho thấy tại sao rule đơn giản kiểu `speed > threshold => noise` là quá sớm.

Có một malformed latitude `400.166667` nằm giữa các point `40.166...`, nhưng ở một trajectory khác lại có pattern lặp đi lặp lại các bước nhảy khoảng 850–862 km chỉ trong một giây. Đây là hai failure mode khác nhau, nên không nên gom chúng vào cùng một rule xử lý.

Điểm quan trọng hơn là 698,900 apparent duplicate timestamps. Ở các trajectory bị ảnh hưởng nặng, trong cùng một giây có nhiều coordinate khác nhau. Vì parser hiện tại dựng timestamp từ date/time text chỉ có độ phân giải một giây, có khả năng EDA đang làm mất sub-second timing và tự tạo ra duplicate timestamp. Cần kiểm tra field `serial_date` trước khi deduplicate hoặc tin hoàn toàn vào speed/sampling summary hiện tại.

Ngoài ra, đã xác nhận có ít nhất một raw trajectory byte-identical nằm trong ba user folders khác nhau. Điều này tạo nguy cơ weighting bias và train/test leakage nếu sau này split trajectory một cách ngây thơ.

Mục tiêu tiếp theo: verify timestamp precision từ `serial_date`, chạy lại timing/speed summary với timestamp semantics đúng, rồi mới đề xuất cleaning rules dựa trên từng failure mode đã đo được thay vì chọn một global threshold ngay từ đầu.
