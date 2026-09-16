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

Ngoài ra, đã xác nhận có ít nhất một raw trajectory byte-identical nằm trong ba user folders khác nhau. Điều này tạo nguy cơ weighting bias và train/test leakage nếu sau này split trajectory một cách ngây thơ.

## 2026-09-16 — Một hypothesis đã được test và bị bác bỏ

Ban đầu mình nghi ngờ field PLT `serial_date` có thể giữ sub-second timing, còn parser dùng `date + time` theo giây đã làm phát sinh duplicate timestamps giả. Kết quả đo không ủng hộ hypothesis đó.

Ở trajectory có 45,215 duplicate text timestamps, khi dựng timestamp từ `serial_date` thì số duplicate vẫn chính xác 45,215. Nhiều coordinate khác nhau trong cùng một giây cũng có cùng `serial_date`. Sai khác vài microsecond giữa serial timestamp và text timestamp chỉ là floating-point conversion noise, không phải thông tin timing bổ sung có ý nghĩa.

Điều này thay đổi cách xử lý preprocessing: các observation cùng giây thực sự mơ hồ ở độ phân giải timestamp của release. Không thể tính within-second velocity hay tự ý gán thứ tự. Cần đo spatial spread của các same-second group trước rồi mới quyết định collapse hay giữ chúng như simultaneous observations.

## 2026-09-16 — Same-second chủ yếu là jitter, nhưng exact duplicates là vấn đề cấu trúc

Phân tích 212,409 same-second groups cho thấy phần lớn rất compact về không gian: median max-radius quanh coordinate-wise median chỉ khoảng 0.47 m, p95 là 4.85 m, p99 là 7.06 m, và 99.61% nằm trong 10 m. Điều này tạo evidence tốt để thử representation một row cho mỗi timestamp bằng robust coordinate đối với các group compact. Phần tail rất xa phải được flag riêng, không được average hai location không tương thích.

Phân tích SHA-256 thay đổi kế hoạch evaluation rõ hơn. Có 821 exact-duplicate hash groups chứa 1,677 files; khoảng 8.98% trajectory files nằm trong ít nhất một duplicate group, và nhiều group trải qua các user ID khác nhau. Vì vậy content identity không phải edge case hiếm. Khi split train/test về sau cần giữ nội dung byte-identical trong cùng fold, đồng thời tránh để duplicated content được weight quá mức trong benchmark.

Mục tiêu tiếp theo: đo riêng cross-user duplicate share và point-weighted impact, prototype same-second consolidation chỉ cho spatially compact groups, rồi tính lại segment speed và temporal gap trước khi đề xuất movement-noise threshold.