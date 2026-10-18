# Stage 10 — Kết luận cuối cùng về Evidence v2 (10a–10l)

**Trạng thái nghiên cứu:** CLOSED / COMPLETED AS AUDIT — **không promote Evidence v2**.  
**Ngày chốt:** 2026-10-15.  
**Nguồn dữ liệu:** các JSON aggregate từ các lần chạy thực tế trên private Modal Volume do operator cung cấp; code kiểm định và synthetic tests trong nhánh \`feature/evidence-v2-offline-audit\`. Không đưa GPS, user ID hay dữ liệu ở mức candidate lên GitHub.

> **Kết luận một câu:** Chúng ta đã chứng minh rằng mức độ *có thể quan sát*, sự *ổn định của một anchor*, và *độ đúng của nhãn HOME/OFFICE* là ba câu hỏi khác nhau. Công thức v2 hiện tại thiếu thành phần đối với phần lớn candidate và không có đủ mẫu holdout có thể đánh giá để chứng minh ưu thế so với v1. Do đó giữ nguyên v1, không deploy v2, đồng thời giữ lại những thành phần Evidence như một hệ thống chẩn đoán minh bạch.

## 1. Mục tiêu và phạm vi quyết định

Câu hỏi xuất phát: thay chỉ số \`evidence_strength=(S+M+H)/3\` của frozen CP2 bằng đề xuất \`E_v2=cbrt(C*O*R)*sqrt(H)\` có giúp lượng hóa bằng chứng HOME/OFFICE tốt hơn hay không?

- \`S\`: tỷ lệ thời gian dwell tại anchor theo khung giờ HOME/ OFFICE.
- \`M\`: chênh lệch share giữa top-1 và runner-up *đủ điều kiện* (theo v1).
- \`H\`: hỗ trợ ngày, bão hòa tại 5 ngày.
- \`C\`: ưu thế tương đối so với *runner-up đủ điều kiện*, không xác định nếu chỉ có một eligible location.
- \`O\`: tỉ lệ support/observed opportunity trong *khung giờ local* tương ứng.
- \`R\`: stability khi che/bỏ bớt dữ liệu quan sát. \`R_train_mask\` của 10l **khác** Stage05 R tính bằng toàn bộ lịch sử.

Tất cả HOME/OFFICE đều là **giả thuyết dựa trên GPS**, không có nhãn semantic ground truth được kiểm chứng độc lập. **Observed recurrence ≠ accuracy**, và \`evidence_strength\` không phải xác suất đúng nhãn.

Các số liệu \`55\` (Stage10a–d trên full-history Stage08 tiers), \`44\` (TRAIN-only emissions ở cutoff 70%) và \`27 HOME / 16 OFFICE\` (frozen production trên toàn lịch sử) thuộc **ba cohort/định nghĩa khác nhau**, không được đồng nhất.

## 2. Kết quả định lượng đã kiểm chứng

### 2.1. Tính đầy đủ của Evidence v2 (10a–10d)

Trên **55 candidate hypotheses** được kiểm tra qua các tier Stage08a/08c (HOME_CORE 27, OFFICE_CORE 16, HOME_PROBABLE 5, HOME_SPARSE_CANDIDATE 4, OFFICE_ROBUST_CANDIDATE 3):

| Kết quả | Số lượng | Ý nghĩa |
| --- | ---: | --- |
| Đủ tất cả thành phần của v2 gốc | 21/55 (38,2%) | Chỉ nhóm có runner-up thực sự mới đủ \`C\`; không đại diện cho toàn bộ 55 |
| Không có eligible runner-up | 34/55 (61,8%) | Stage10c xác minh **34 thực sự là singleton eligible**, không phải lỗi join |
| Thiếu Stage05 \`R\` | 4/55 | Đều thuộc HOME_SPARSE_CANDIDATE 2-of-2, chồng lấp nhóm thiếu runner-up |
| Opportunity invalid | 0/55 | Không phát hiện lỗi denominator ở audit đầu vào |

Với **TRAIN-only 70%** trong Stage10h/10l, **33/44 emitted** chỉ có 1 eligible anchor và vì v1 zero-fills runner-up, \`M=S\`. Ở các trường hợp này v1 thực chất là \`(2*S+H)/3\`; hai hạng tử share không phải hai nguồn bằng chứng độc lập. Đây là **hạn chế cần diễn giải**, không phải lý do tự sửa score trong production.

**Kết luận:** V2 nguyên bản có vấn đề **coverage do thiết kế và cơ chế chọn mẫu**. Không được tùy tiện \`C=1\`, \`C=0\` hay coi singleton là không có địa điểm cạnh tranh ngoài đời.

### 2.2. Khả năng quan sát và tái xuất hiện trong FUTURE (10e–10i)

Protocol 70/30: cắt theo ngày UTC arrival được quan sát trong lịch sử từng người; fit frozen complete-link CP2 **chỉ trên TRAIN**; đánh giá GPS FUTURE theo IANA local HOME-night/ OFFICE-weekday window, yêu cầu **>=600 giây/ngày**, và chỉ match vào một TRAIN cluster khi FUTURE stay cách **mọi TRAIN member <=200 m**, unique match. Đây là retrospective temporal evaluation, không phải deployment simulation.

- TRAIN có stays: **114 users**; phát ra **44 anchors** (HOME 27, OFFICE 17).
- FUTURE có khung thời gian phù hợp: **43/44** anchors.
- Có ít nhất 1 ngày FUTURE đủ unique spatial match với một TRAIN location: **31/43**.
- Trong 31 spatially assessable: **25** thấy lại đúng selected TRAIN anchor; **6** thấy TRAIN anchor khác.
- **12/43** có GPS đúng khung giờ nhưng không có ngày đủ support unique spatial match.

| FUTURE 70/30 | HOME | OFFICE | Tổng |
| --- | ---: | ---: | ---: |
| Time-observable | 27 | 16 | 43 |
| Unique-spatial observable | 21 | 10 | 31 |
| Same selected anchor reappears | 17 | 8 | 25 |
| Other TRAIN anchor, not selected | 4 | 2 | 6 |
| Spatially unresolved | 6 | 6 | 12 |

Có **25/43 (58,1%)** observed recurrence nếu điều kiện chỉ là FUTURE time opportunity; **25/31 (80,6%)** nếu *chỉ xét* FUTURE spatially assessable. Hai tỷ lệ **không mâu thuẫn** vì denominator khác. Tỷ lệ 80,6% chịu selection bias mạnh và **không phải semantic accuracy**. Kể cả 6 trường hợp ở TRAIN anchor khác cũng không chứng minh selected anchor gắn sai nhãn HOME/OFFICE.

### 2.3. Cutoff sensitivity và đánh giá đúng cùng FUTURE (10j–10k)

Stage10j trên cùng người dùng (không độc lập) ghi nhận:

| TRAIN/FUTURE | TRAIN emitted | FUTURE time | FUTURE unique spatial | Same selected anchor | Spatial unresolved |
| --- | ---: | ---: | ---: | ---: | ---: |
| 60/40 | 40 | 40 | 34 | 27 | 6 |
| 70/30 | 44 | 43 | 31 | 25 | 12 |
| 80/20 | 43 | 40 | 29 | 21 | 11 |

Tỷ lệ \`same / unique spatial\` tương ứng **27/34 (79,4%)**, **25/31 (80,6%)**, **21/29 (72,4%)**. Chúng không phải ba lần kiểm định độc lập; cả candidate composition và FUTURE duration đều đổi.

Stage10k so sánh **user-label cùng được emit** trên đúng FUTURE chung của từng cặp; **không so sánh integer location_id giữa lần fit**:

| Cặp TRAIN | Emitted ở cả hai | Hình học TRAIN compatible (all-member 200m) | Early-only emitted | Late-only emitted |
| --- | ---: | ---: | ---: | ---: |
| 60→70 | 38 | 38/38 | 2 | 6 |
| 70→80 | 42 | 42/42 | 2 | 1 |
| 60→80 | 36 | 36/36 | 4 | 7 |

Địa điểm TRAIN được chọn trong nhóm emitted-overlap **tương thích không gian** theo ngưỡng 200m (không có trường hợp separated/partial), nhưng việc *được emit* không bất biến. Khi giữ cùng FUTURE giữa 70→80, **OFFICE same-anchor là 5/15 cho mỗi mô hình** trên nhóm cả hai emit và time-observable; vì vậy không được diễn giải chênh lệch tỷ lệ OFFICE unpaired Stage10j là bằng chứng rằng tăng TRAIN gây giảm độ ổn định anchor.

Ngay cả trên cùng FUTURE, spatial assessability đổi theo TRAIN geometry: trong 40 cặp time-observable 70→80, **24** cả hai mô hình assessable, **1** chỉ early, **5** chỉ late, **10** không mô hình nào assessable. Unmatched/ambiguous không đủ để phân biệt GPS jitter, địa điểm mới, khác biệt hành vi hay geometry nghiêm ngặt.

### 2.4. Head-to-head v1/v2 (Stage10l, operator run PASS)

Stage10l tính lại TRAIN-only S/M/H/O/C, đúng v1 parity, tạo **R_train_mask từ 9 trials chỉ dùng TRAIN** và áp công thức v2 **không thay đổi**. Nguồn FUTURE chỉ được join sau khi tính score. Stage10i/10j 70% parity PASS.

| Cohort | Kết quả |
| --- | ---: |
| TRAIN emitted | 44 |
| FUTURE time-observable | 43 |
| FUTURE spatially observable | 31 |
| V2 scorable trong 44 emitted | 11 |
| V2 scorable + FUTURE spatially observable | **9** |
| Trong cùng 9: same anchor / other TRAIN anchor | **7 / 2** |
| V2 không có score do singleton eligible | **33/44** |
| Trong 31 spatially observable, không có v2 score | **22/31** |
| Pairwise concordance v1 vs v2 (minimum 5 mỗi outcome) | **NULL / không ước lượng được** |

\`R_train_mask\` median trên 44 candidates là 0,777778; nhóm multiple-eligible n=11 median 1,0; singleton n=33 median 0,666667. Đây chỉ là một *TRAIN-only perturbation proxy*, không phải xác suất hoặc chính R của Stage05.

**Quan trọng:** median v1 hay median v2 trong nhóm \`reappeared\` không cho phép so sánh độ tốt của hai thang điểm vốn khác định nghĩa. Với chỉ **2 negative/other-anchor** trong matched cohort, không thể kiểm định liệu thứ tự xếp hạng của v2 có hơn v1 hay không. Không tăng denominator bằng cách ép 22 case v2-missing thành score 0 hoặc coi 12 spatially unresolved là sai.

## 3. Kết luận khoa học: điều biết và chưa biết

**Có bằng chứng hỗ trợ:**

1. Pipeline có các parity guards: original CP2, TRAIN-only 70%, 10i/10j, 10k, 10l; các lần chạy riêng tư được operator báo PASS. Chúng xác nhận tính nhất quán với **định nghĩa hiện tại**, không xác nhận semantic truth.
2. Khả năng quan sát theo thời gian, spatial matching và recurrence là ba trạng thái khác nhau, phải báo cáo riêng.
3. Thiếu eligible runner-up là trạng thái *structural missingness* thường gặp và không ngẫu nhiên; v2 \`C\` khiến phần lớn candidate bị loại khỏi so sánh.
4. Các TRAIN anchors **cùng được emit qua các cutoff** không cho thấy dịch chuyển hình học vượt 200m theo định nghĩa Stage10k, nhưng candidate emission/matching coverage thay đổi theo cutoff.
5. Một biến độ ổn định đo từ toàn bộ lịch sử không được đem vào mô hình TRAIN để đánh giá trên FUTURE cùng giai đoạn.

**Chưa được chứng minh:**

- HOME/OFFICE semantic accuracy, precision/recall/F1/AUC đối với nhãn thực; không có independent ground truth.
- Evidence v1 tối ưu hay tốt hơn v2; **v2 cũng không được chứng minh tốt hơn v1**.
- Score v1 hoặc v2 là xác suất đúng nhãn; không có calibration.
- Khả năng tổng quát trên người dùng/đô thị khác; 60/70/80 là nested correlated cuts của cùng người dùng, không phải replication.
- V2 hoạt động tốt với singleton/sparse users, hoặc có thể triển khai mà không thay đổi chính sách abstain.

## 4. Quyết định ADR — Freeze & stop tại Stage 10l

| Quyết định | Trạng thái |
| --- | --- |
| Frozen CP2 full-history emissions (27 HOME / 16 OFFICE) | **Giữ nguyên** |
| Production \`evidence_strength\` v1, complete-link 200m và các gate HOME/OFFICE | **Giữ nguyên** |
| Đề xuất \`cbrt(C*O*R)*sqrt(H)\` làm production score | **Không promote / không deploy** |
| Stage08c candidate tiers, AWS PR #73, API và hạ tầng | **Không thay đổi** |
| Rerun CP1, rebuild GPS, bật EC2, thay threshold baseline | **Không thực hiện trong Stage 10** |
| Stage 10a–10l | **Đóng nghiên cứu offline audit; không mở 10m để săn kết quả** |
| \`C\` không có peer / thiếu \`R\` / spatial FUTURE unresolved | **Abstain / báo rõ lý do, không tự điền** |

Quyết định **không deploy** không đồng nghĩa chứng minh v2 là sai: nó chưa đủ coverage và chưa có external outcome chứng minh tác dụng. Tách **Factorized Evidence** thành 3 khía cạnh nghiên cứu: (a) location concentration/support, (b) observation opportunity/quality, (c) TRAIN-derived identity/behavioral stability. Các trục này có thể được hiển thị riêng trong nghiên cứu; **không** tự động ghép thành xác suất.

## 5. Khuyến nghị bước tiếp theo, ngoài Stage 10

Không lập Stage 10m chỉ để tinh chỉnh v2 trên 9 observation. Tạo **nhánh/thực nghiệm riêng** cho câu hỏi của sản phẩm: tại sao HOME/OFFICE coverage thấp và liệu baseline gate có quá strict.

Thứ tự hợp lý:

1. **Data lineage/trajectory assembly audit:** xác minh ghép file PLT của từng user, overlap, duplicate, thứ tự thời gian, sampling gap, cross-file continuity, UTC/local chronology; đo ảnh hưởng trước khi chỉnh thuật toán (không thay đổi các reference baseline).
2. **Baseline eligibility waterfall** trên cả user có/không có emitted HOME/OFFICE: bao nhiêu bị loại ở cleaning/stay detection, địa điểm lặp, relevant local date support, share/margin, spatial matching; phân tầng SPARSE/MEDIUM/DENSE, HOME/OFFICE. Đây là **chẩn đoán coverage**, không dùng FUTURE để chọn thresholds.
3. **Sensitivity của strict gates** (\`min_dates\`, dwell \`share\`, \`margin\`, cleaning gap/distance) một biến mỗi lần trên cache với fixed cohorts; luôn ghi recall/coverage proxy, abstentions, identity transitions và false-positive risks, có TRAIN/FUTURE tách rời nếu kiểm chứng recurrence. **Không âm thầm thay đổi production**.
4. **Dữ liệu có verified semantic HOME/OFFICE truth**, hoặc độc lập ngoài GeoLife, trước khi thử lại score confidence. Lúc đó cần định nghĩa outcome & missingness, báo confidence intervals theo user và benchmark đồng cohort bao gồm singleton, mới cân nhắc replace v1.

Đây là **roadmap đề xuất**, chưa thực hiện trong PR #74. Mọi nới lỏng thresholds hoặc tính score mới phải là thí nghiệm riêng với acceptance gates riêng.

## 6. Source of truth, reproducibility & privacy

- Protocol/source/từng experiment: [\`docs/eda/44_evidence_v2_offline_audit.md\`](44_evidence_v2_offline_audit.md), \`analysis/10*_*.py\`, \`tests/test_evidence_v2_*.py\`.
- Operator-provided aggregate Stage10l: \`/mnt/geolife-data/cache/cp2_v2/10_evidence_v2_offline/train_only_v1_v2_paired_aggregate.json\` (private Modal Volume; JSON data reflected **only as aggregate counts** in this report).
- Historical 10f/10i/10j/10k aggregates are described in Stage44 and worklog. Candidate user IDs, coordinates, stay-level and private PKL remain on Modal Volume, not shared through PR.
- CI/Docker smoke validate code paths and synthetic fixtures; they **do not run private GeoLife actual experiments**. Real-data run status above is operator-reported, not independently reproduced by GitHub Actions.
- Source counts refer to retrospective observed UTC arrival-date split with per-stay local timezone resolution. No independent prospective claim.

**Research closure criterion met:** defined question evaluated within available data; observed evidence insufficient for superior/representative Evidence v2 ranking; safe non-promotion decision documented, no deployed change. Reopen only with **new evidence** (independent labels, broader representativeness, missingness-aware candidate coverage) rather than more tuning on current selected cohorts.
