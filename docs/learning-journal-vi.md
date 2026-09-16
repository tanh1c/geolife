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

Mục tiêu tiếp theo: chạy notebook trên dataset thật, tự giải thích các distribution chính, rồi dùng evidence để đề xuất cleaning/stay-point threshold candidates.
