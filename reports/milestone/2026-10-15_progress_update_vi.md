# GeoLife — Báo cáo tiến độ cập nhật ngày 15/10/2026

**Giai đoạn cập nhật:** Sau bản báo cáo dự kiến ngày 13/10/2026.  
**Mốc hiện tại:** Hoàn thiện **MLE serving nội bộ trên AWS** (đã chạy demo sync, canary và rollback qua SSM) đồng thời **khép lại chuỗi thực nghiệm Evidence v2 Stage 10a–10l**. Chưa phải public/production release.

## 1. Công việc đã hoàn thành

### EDA, CP1/CP2 và baseline

- Giữ nguyên baseline đã chốt: **5.821 stays, 136 users có stays, 27 HOME và 16 OFFICE**. CP2 sử dụng **complete-link 200 m**, timezone IANA theo từng stay và khả năng **abstain** khi thiếu bằng chứng; không thay các ngưỡng production.
- Các nghiên cứu mở rộng coverage Stage 08a–08c giữ riêng khỏi baseline: tối đa **HOME 36 / OFFICE 19** trong các *research tiers*, **không** phải nhãn đã deploy. Stage 09 kiểm tra cách nối file trajectory (đối chứng 5.831 so với 5.821 stays) nhưng không tạo thêm user có stay hoặc nhãn HOME/OFFICE; chưa migrate pipeline.

### Serving và kiểm thử mô hình

- **PR #72 đã merge vào \`main\`**: FastAPI v2, Docker, UI bản đồ có đăng nhập và phân quyền tài khoản nội bộ; hỗ trợ GPS mới (\`JSON\`/\`.plt\`) và private GeoLife cache theo account được cấp quyền; có quản lý phiên, thu hồi phiên và bảo vệ đường inference không xác thực trong demo restricted.
- Hai biến thể thật: **complete-link 200 m (baseline)** và **DBSCAN 100 m (candidate)**. Có authenticated account-sticky routing, canary và rollback; E2E trên private Modal cache đã được người vận hành báo PASS (HOME, OFFICE, recurring-abstain và no-stay).

### AWS infrastructure và triển khai sync demo

- IAM user \`geolife-ops\` đăng nhập bằng phiên tạm thời, không dùng root/long-lived access keys; phân quyền bằng IAM groups/inline policies, EC2 instance profile chỉ đủ SSM, ECR pull và CloudWatch Logs. **Không triển khai IAM Identity Center**.
- Terraform đã provision **5 tài nguyên**: EC2 \`c7i-flex.large\`, ECR repository, ECR lifecycle policy, CloudWatch Logs group và Security Group **zero inbound**, outbound TCP/443. EC2 SSM **Online trong lúc kiểm thử**.
- **Mốc mới so với bản 13/10:** đã build/push Docker image lên ECR, chạy FastAPI container trên EC2 loopback và truy cập bằng **SSM port forwarding**. Kiểm tra \`/health\` và \`/demo\` trả HTTP 200; yêu cầu protected không xác thực trả HTTP 401; synthetic account \`demo_000\` chạy được inference. CloudWatch \`/geolife/dev/api\` đã có log events.
- Kiểm thử **baseline → 100% DBSCAN canary → rollback baseline** bằng synthetic requests qua SSM đều PASS. Latency client-observed, đơn vị ms:

| Chế độ | HTTP thành công | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: |
| Baseline complete-link | 50/50 | 127 | 157 | 179 |
| Canary 100% DBSCAN | 50/50 | 146 | 273 | 512 |
| Rollback về baseline | 10/10 | 127 | 201 | 234 |

Đây là **benchmark synthetic, một tài khoản sticky, không có concurrent load**; không dùng để khẳng định model nào có hiệu năng tổng quát tốt hơn. Chưa đo tỷ lệ routing 90/10 trên nhiều tài khoản.

### Nghiên cứu bổ sung — Evidence v2 (Stage 10a–10l)

- Kiểm tra **55 candidate hypotheses** của các tier: công thức Evidence v2 đầy đủ chỉ tính được cho **21/55**; **34/55** chỉ có một địa điểm *đủ điều kiện* theo ranker, nên không xác định được thành phần so với runner-up. Đây là hạn chế coverage của công thức, không phải lỗi ghép dữ liệu.
- Forward validation chia TRAIN/FUTURE **70/30**: 44 TRAIN anchors; 43 có GPS đúng khung giờ FUTURE; **31** đủ unique spatial matching; **25** thấy lại anchor cũ, **6** thấy TRAIN anchor khác và **12** chưa đủ bằng chứng đối chiếu không gian. **25/31 = 80,6% là recurrence có điều kiện, không phải HOME/OFFICE accuracy.**
- Sensitivity cutoffs **60/70/80** và paired common-FUTURE audit kiểm tra sự ổn định hình học: trong các cặp đều được emit, **38/38, 42/42 và 36/36** anchors tương thích ở ngưỡng 200 m; tuy nhiên việc emit và spatial observability vẫn thay đổi.
- So sánh TRAIN-only Evidence v1/v2 (Stage 10l): v2 tính được trên **11/44**, nhưng chỉ **9** có đủ spatial observability để so sánh công bằng (7 recurrence, 2 quan sát TRAIN anchor khác). **Không đủ mẫu để kết luận v2 xếp hạng tốt hơn v1**. Đã chốt **không thay thế Evidence v1**, không dùng v2 như xác suất đúng nhãn và kết thúc nhánh nghiên cứu Stage 10 ở mức offline audit.

## 2. Trạng thái tại thời điểm báo cáo

**Đạt mốc: Restricted AWS Sync Demo Validated + Evidence v2 Research Audit Closed.**

- **PR #72:** merged. **PR #73:** AWS serving/deployment đã có bằng chứng thử nghiệm, **vẫn open, chưa merge**. **PR #74:** nghiên cứu Evidence v2 đã tổng kết, **vẫn open, chưa merge**. Python CI và Docker smoke PASS ở head commit đã kiểm tra của cả PR #73/#74 trước các bổ sung báo cáo.
- **Không có public API**, không mở inbound EC2, không upload private GeoLife historical cache lên AWS, không thay model/score production. Trạng thái EC2 **sau yêu cầu dừng** và chi phí còn phát sinh chưa được xác minh độc lập; không khẳng định đã tắt/destroy.
- Các hạng mục còn thiếu so với roadmap Track B1: **async SQS worker/jobs**, kiểm thử routing **90/10 nhiều tài khoản** nếu là yêu cầu nghiệm thu, **monitoring dashboard**, concurrent-load benchmark và **offline simulated drift replay**. Chưa thể gọi Checkpoint B1 hoàn thành toàn bộ.

## 3. Công việc tiếp theo theo roadmap

1. **Hoàn thiện handoff AWS sync:** rà soát và quyết định merge PR #73; kiểm tra trạng thái EC2/EBS/ECR/CloudWatch và cost/budget, giữ Terraform state an toàn. Nếu cần, kiểm thử sticky 90/10 với nhiều synthetic accounts; không lặp lại bài 100% canary đã PASS chỉ để có thêm log.
2. **Triển khai async proof of concept:** \`POST /v2/jobs\` → lưu synthetic payload trong private encrypted TTL storage → đưa **job ID/pointer, không đưa GPS** vào SQS → worker xử lý, retry/idempotency/DLQ → \`GET /v2/jobs/{job_id}\` có xác thực. So sánh sync/async latency và error/timeout.
3. **Bổ sung observability và demo pack:** metrics latency/error/abstention theo model, CloudWatch dashboard, replay drift được ghi rõ **simulated_offline_replay**, kiến trúc, canary/rollback, cost và teardown evidence.
4. **EDA tiếp theo, tách riêng serving:** audit nối các file \`.plt\` và chronology/duplicate/gap; dựng **CP1→CP2 eligibility waterfall** để tìm nơi mất HOME/OFFICE coverage; sau đó mới làm sensitivity một ngưỡng mỗi lần trên baseline cố định. Chưa tự động nới production gates hay promote các tier research.

## 4. Tham chiếu

- [PR #72 — Serving v2 / authenticated demo (merged)](https://github.com/tanh1c/geolife/pull/72)
- [PR #73 — AWS SSM-only deployment & canary (open)](https://github.com/tanh1c/geolife/pull/73)
- [PR #74 — Evidence v2 offline audit (open)](https://github.com/tanh1c/geolife/pull/74)
- [Stage 10 — Báo cáo kết luận và quyết định](../../docs/eda/45_evidence_v2_final_decision.md)
- [Track B1 — Roadmap và checkpoint mới nhất](../../docs/roadmap/track_b1_delivery_roadmap.md)

*Các kết quả AWS và Modal nêu trên dựa trên output thực nghiệm do người vận hành báo cáo; CI/Docker smoke dùng synthetic fixtures, không tái chạy private GeoLife dữ liệu trên GitHub.*
