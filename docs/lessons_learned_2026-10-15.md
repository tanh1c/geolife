# Lessons Learned — GeoLife checkpoint ngày 15/10/2026

Đây là bản tóm tắt các bài học để tái sử dụng trong roadmap và mentor report; diễn giải chi tiết nằm trong \`docs/learning-journal-vi.md\`, \`docs/learning-journal-en.md\`, \`docs/worklog.md\`, và \`docs/eda/45_evidence_v2_final_decision.md\`.

## 1. Luôn tách “đã chạy” khỏi “đã sẵn sàng production”
- AWS SSM-only nội bộ đã được người vận hành chứng minh với synthetic requests, CloudWatch log events, baseline/100% canary/rollback.
- Chưa public HTTPS, chưa nhận real-user requests, chưa xác minh 90/10 routing theo nhiều account, chưa concurrent-load hoặc SQS async.
- CI PASS xác nhận code/test fixtures, không thay thế private-Modal/AWS human-observed proof.

## 2. Canary một tài khoản không nói được traffic allocation toàn hệ thống
- Sticky routing cố định model theo account. Một account benchmark lặp lại 50 lần chỉ xác nhận định tuyến ổn định của account đó.
- Trong bài thử qua SSM, baseline p50/p95/p99 = 127/157/179 ms, DBSCAN 100% = 146/273/512 ms, rollback = 127/201/234 ms. Không suy ra latency tổng quát hay causal model comparison.

## 3. Debug môi trường trước khi mở IAM
- CloudWatch Logs command thất bại do Git Bash MSYS chuyển đổi slash-argument, được giải quyết bằng \`MSYS_NO_PATHCONV=1\`.
- Không nới IAM nếu chưa chứng minh đó thực sự là authorization error.

## 4. Missing feature không phải negative evidence
- Stage10a–d có 34/55 candidate không có eligible runner-up, nên thành phần C của v2 không xác định; không coi C=0 hay C=1.
- Stage10l 33/44 TRAIN-only candidates là eligible singleton, 11/44 có v2 score, 9/31 FUTURE-spatial-assessable có thể so sánh. Chỉ 2 trường hợp other-anchor: ranking comparison không ước lượng được.

## 5. Tách observation opportunity, spatial resolution, behavioral recurrence, semantic truth
- Stage10i 43/44 time-observable, 31 unique-spatial-observable, 25 exact anchor recurrence, 6 observed at other TRAIN anchor, 12 spatial-unresolved.
- 25/31 (80,6%) là conditional recurrence **với selection bias**, không phải accuracy.
- Không nhập full-history Stage05 R vào TRAIN để kiểm định FUTURE; Stage10l dùng proxy R từ 9 masks TRAIN-only.

## 6. Giữ baseline đã thẩm định để làm đối chứng
- Không đổi CP2 5.821 stays, 27 HOME /16 OFFICE, complete-link 200m, v1 evidence và abstain gates.
- Stage08c HOME36/OFFICE19 chỉ là research tiers; Stage09 stitching và Stage10 v2 đều chưa phải migration.

## 7. Ưu tiên delivery đúng scope, rồi mở nghiên cứu coverage riêng
- Trước mắt: PR #73 review, chi phí/teardown, optional 90/10, SQS job async, monitoring dashboard và offline-simulated drift/replay.
- Sau đó: audit cách ghép .plt, eligibility waterfall qua CP1→CP2, thử độ nhạy từng strict threshold, thu independent semantic labels nếu cần claim accuracy.

**Decision checkpoint:** Stage10a–10l đã đóng về mặt research audit; **không promote v2**. PR #73/#74 vẫn phải review, không auto-merge hoặc deploy thêm từ trang lessons này.
