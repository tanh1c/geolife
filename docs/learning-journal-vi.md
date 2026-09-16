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

Phân tích SHA-256 thay đổi kế hoạch evaluation rõ hơn. Có 821 exact duplicate hash groups chứa 1,677 files; khoảng 8.98% trajectory files nằm trong ít nhất một duplicate group, và nhiều group trải qua các user ID khác nhau. Vì vậy content identity không phải edge case hiếm. Khi split train/test về sau cần giữ nội dung byte-identical trong cùng fold, đồng thời tránh để duplicated content được weight quá mức trong benchmark.

## 2026-09-16 — Cross-user duplication đủ lớn để ảnh hưởng evaluation

Cả 821 exact-duplicate hash groups đều trải qua nhiều user ID. 1,677 files bị ảnh hưởng chiếm 8.98% số trajectories nhưng chứa 2,965,977 GPS points, tương đương 11.92% toàn dataset.

Điểm quan trọng là point-weighted exposure lớn hơn file-count exposure, nghĩa là các duplicate trajectories có xu hướng dài hơn trung bình và có thể ảnh hưởng metric theo point mạnh hơn tưởng tượng nếu chỉ nhìn số file. Dataset không giải thích vì sao cùng content lại nằm dưới nhiều user ID, nên không được suy diễn rằng các user ID đó là cùng một người. Tuy nhiên ở góc độ evaluation, content hash phải được dùng như grouping key để tránh identical traces rơi vào hai fold khác nhau.

## 2026-09-16 — Redundancy và connected components làm thay đổi split strategy

Sau khi giữ lại một representative cho mỗi exact-content hash group, các bản copy dư vẫn chiếm 1,495,115 points, tương đương 6.01% toàn dataset. Điều này làm rõ hai khái niệm: 11.92% là số points nằm trong các duplicate groups, còn 6.01% mới là phần point mass dư thừa vượt quá một representative.

User graph tạo bởi shared exact content có 52 users nằm trong 18 connected components; component lớn nhất chứa 15 user IDs. Vì vậy ngay cả user-level split cũng chưa đảm bảo content independence: các user ID khác nhau vẫn có thể được nối với nhau bằng byte-identical trajectories. Với strict evaluation, content-hash grouping là bắt buộc; connected-component grouping là candidate hợp lý nếu muốn đo user-level generalization nghiêm ngặt hơn.

Một bài học khác là biết điểm dừng của EDA. Phần duplicate structure hiện đã đủ evidence cho CP1; tiếp tục đào sâu sẽ dễ biến EDA thành project riêng. Trọng tâm tiếp theo nên quay lại preprocessing phục vụ stay-point detection: same-second consolidation, temporal gaps và movement anomalies.

## 2026-09-16 — Same-second consolidation giải quyết một failure mode, không phải tất cả

Prototype consolidation làm rõ sự khác nhau giữa các failure mode. Với một trajectory có nhiều duplicate timestamps, 56,780 raw points được collapse còn 11,565 timestamp rows và chỉ có 3 spatial conflicts. Các max speed lớn nhất sau consolidation giảm còn khoảng 225 km/h. Đây là evidence cho thấy timestamp-resolution ambiguity thực sự ảnh hưởng tới cách tạo segment.

Nhưng cùng transform đó không sửa được trajectory corrupted của user 062. Nó flag được 26 same-second conflicts, trong khi các jump hàng trăm km giữa những singleton timestamps ở các giây khác nhau vẫn còn và vẫn tạo speed cỡ hàng triệu km/h. Vì vậy same-second ambiguity và impossible movement giữa các timestamp khác nhau là hai vấn đề cleaning độc lập.

Bài học chính là preprocessing nên có nhiều stage dễ giải thích: validate coordinate trước, collapse same-second group compact tiếp theo, rồi mới xử lý temporal gap và movement anomaly. Global speed threshold chỉ nên được cân nhắc sau khi các failure mode trước đã được xử lý hoặc flag.

## 2026-09-16 — Full consolidation thay đổi cách đọc speed tail

Khi áp dụng same-second consolidation trên toàn release, 24,876,978 raw points giảm còn 24,178,077 timestamp-level rows, tức giảm 2.81%, trong khi chỉ có 835 timestamps (0.0035%) bị spatial conflict. Đây là evidence mạnh rằng transform này xử lý đúng pattern duplicate-second chính mà không làm mất nhiều observation hợp lệ.

Kết quả quan trọng hơn là speed tail còn lại gần như không biến mất. Ở trajectory level, 46.96% trajectories vẫn có max speed >100 km/h, nhưng ở segment level chỉ 5.40% valid movement segments vượt 100 km/h. Trên 150 km/h chỉ còn khoảng 1.00%, trên 200 km/h khoảng 0.37%, và trên 1,000 km/h chỉ 0.007%.

Điều này cho thấy trajectory-max và segment prevalence trả lời hai câu hỏi khác nhau. Chỉ một bad segment cũng đủ làm cả trajectory trông extreme, nên cleaning threshold phải được reasoning ở segment level rồi mới truy ngược về trajectory/user.

Temporal gap là một failure mode độc lập khác: median của trajectory max-gap là 325 giây, p90 khoảng 11,010 giây, còn maximum là 93,298 giây. Với stay-point detection, hai point gần nhau nhưng bị ngăn bởi một observation outage dài không thể tự động được hiểu là user đã dwell liên tục tại đó.

## 2026-09-16 — Gap sensitivity cho thấy continuity phải được định nghĩa rõ

Sensitivity table làm vấn đề temporal continuity cụ thể hơn. Hơn một nửa trajectories có ít nhất một gap dài hơn 5 phút, 41.74% có gap dài hơn 10 phút, và 29.66% có gap dài hơn 30 phút. Nếu dùng threshold rất chặt như 30–60 giây thì phần lớn trajectories sẽ bị split ít nhất một lần.

Vì vậy gap threshold không phải implementation detail nhỏ. Nó quyết định observation nào được phép đóng góp vào cùng một dwell interval, nên cần được coi là sensitivity parameter và được justify bằng behavior của stay-point detector thay vì chọn theo convenience.

Parser transportation labels tạo ra 14,718 intervals trên 69 user folders. Walk chiếm nhiều interval nhất, sau đó là bus, bike, taxi, car, subway và train; airplane chỉ có 17 intervals. Các labels này hữu ích để kiểm tra speed tail hợp lý của movement thật, nhưng chỉ là auxiliary evidence, không phải ground truth Home/Office.

## 2026-09-16 — Transportation labels cho thấy shape của speed hợp lý nhưng labels có ambiguity

Join strict-containment đầu tiên match được khoảng 4.85 triệu segments, tương đương 40.83% valid segments của nhóm users có labels. Distribution theo mode nhìn broadly hợp lý để làm auxiliary evidence: airplane có median/p99 khoảng 624/938 km/h, train khoảng 93/210, car khoảng 30/120, bus khoảng 17/90, walk khoảng 4/41 và bike khoảng 11/41.

Kết quả này đủ để bác bỏ ngay rule global `speed > 500 km/h => noise`: hơn một nửa airplane segments đang match vượt 500 km/h. Ngược lại, các mode không phải airplane vẫn có một số max speed lên tới hàng nghìn km/h, nên việc segment nằm trong một transportation label không có nghĩa segment đó chắc chắn sạch.

Finding quan trọng nhất là 1,903 label intervals overlap hoặc touch interval trước đó theo integrity check hiện tại, trong đó có những overlap thật giữa các mode khác nhau. Vì vậy `merge_asof` hiện tại có thể chọn một label trong khi đồng thời còn label khác cũng active. Các percentile theo mode hiện tại chỉ là provisional. Trước khi dùng chúng để freeze speed rule, cần canonicalize labels và chỉ benchmark các khoảng thời gian có đúng một distinct active mode.

## 2026-09-16 — Canonicalize labels cho thấy overlap nhỏ nếu đo theo duration

Sau khi canonicalize, chỉ giữ các window có đúng một mode active và loại những khoảng có nhiều mode khác nhau cùng active. Kết quả có 14,537 unambiguous windows và 1,886 ambiguous windows.

Điểm cần nhìn là thời lượng chứ không phải số window: unambiguous time là 12,723.9 giờ, ambiguous time chỉ 76.9 giờ, tức 0.60% represented labeled time. Các conflict phổ biến nhất là bus+walk, bike+walk, taxi+walk và subway+walk. Nhiều ambiguous window chỉ dài một giây, dù vẫn có một số overlap dài đáng kể.

Khi process lại toàn bộ labeled users bằng canonical windows, V2 match được 4,812,641 segments, tương đương khoảng 40.52% coverage. So với benchmark provisional, chỉ mất 37,217 segments, khoảng 0.77% số segments từng match. Vì vậy broad speed shape khó có khả năng chỉ là artifact do label overlap, nhưng vẫn cần bảng per-mode V2 cuối cùng trước khi freeze decision về speed cleaning.

## 2026-09-16 — Benchmark speed cuối đã đóng vòng EDA

Bảng canonical V2 gần như không thay đổi so với provisional: p99 của mọi mode chỉ thay đổi dưới 0.5 km/h. Airplane vẫn khoảng 625 km/h ở median và 938 km/h ở p99; train khoảng 93/210; car khoảng 30/120; bus khoảng 17/91; bike khoảng 11/41; walk khoảng 4/40.

Đây là evidence đủ để dừng việc chọn threshold bằng intuition. Các rule global 100, 200 hay 500 km/h đều không phù hợp với dataset này vì sẽ loại legitimate fast travel; 52.89% canonical airplane segments vượt 500 km/h. Đồng thời những giá trị hàng nghìn km/h hiếm gặp trong các mode thông thường cho thấy vẫn cần một corruption guard bảo thủ.

Compromise được đề xuất là hard guard 1,200 km/h riêng cho release này và chỉ dùng để break continuity, tuyệt đối không dùng để quyết định endpoint nào phải xóa. Guard này giữ toàn bộ canonical airplane segments đã quan sát, với max khoảng 1,048 km/h, đồng thời bắt các corruption cực đoan. Bài học thiết kế quan trọng là: khi evidence cho biết một segment không đáng tin nhưng không cho biết endpoint nào sai, break continuity an toàn hơn việc tự bịa ra một repair.

EDA cho cleaning decision này đã đóng. Bước tiếp theo là review contract, rồi viết test RED trước khi implement preprocessing hoặc stay-point production code.
