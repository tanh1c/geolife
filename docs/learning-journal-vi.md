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

## 2026-09-16 — Canonicalize labels theo inclusive-end (lịch sử)

Run canonicalization đầu tiên dùng inclusive-end semantics, tạo ra 14,537 unambiguous windows và 1,886 ambiguous windows; V2 strict-containment match 4,812,641 segments, khoảng 40.52% coverage. Kết quả này được giữ lại như lịch sử reasoning, không còn là số report cuối.

Broad speed shape của V2 vẫn đủ để đặt câu hỏi đúng về global speed cutoff, nhưng exact interval accounting sau đó đã được audit lại.

## 2026-09-17 — Interval semantics là một phần của data contract

Independent audit chỉ ra một lỗi semantics nhỏ nhưng quan trọng: nếu coi transportation labels có end-time inclusive thì nhiều cặp chỉ chạm endpoint bị biến thành overlap 1 giây. Convention cuối cùng được chốt là half-open `[start, end)`.

Final rerun cho kết quả: 1,742 cặp khác mode chỉ chạm endpoint, 146 cặp overlap thật, 14,583 unambiguous canonical windows, 149 atomic ambiguous sweep slices và 138 report-level ambiguous windows. Tổng unambiguous time là 12,720.833 giờ, ambiguous time là 76.345 giờ, tương đương 0.597% represented labeled time.

V3 strict-containment match 4,807,087 / 11,878,198 valid segments của labeled users, coverage 40.47%. Speed distribution gần như không đổi: airplane p99 937.99 km/h, train 210.34, car 119.63, bus 90.59, bike 40.63 và walk 40.39. Airplane max vẫn 1,048.11 km/h và 52.92% canonical airplane segments vượt 500 km/h.

Bài học chính không chỉ dành cho GeoLife: boundary semantics như `[start, end)` hay `[start, end]` phải được coi là một phần của data contract. Chỉ một khác biệt nhỏ ở boundary cũng có thể làm event/window counts thay đổi mạnh, dù kết luận theo duration vẫn ổn định.

Audit này cũng cho thấy cách dừng EDA đúng lúc: correction đã được independently reproduce, rerun bounded và không làm đổi design decision. Vì vậy EDA cho CP1 được đóng tại đây. Bước tiếp theo là review/approve cleaning + stay-point contract, sau đó viết RED tests trước khi implement production preprocessing/stay-point code.

## 2026-09-18 — Threshold có thể nghĩa là “safe để transform”, không phải “valid hay corrupt”

Góp ý của mentor về same-second làm rõ một distinction quan trọng. Rule 10 m ban đầu rất dễ bị diễn giải thành ngưỡng phân biệt data tốt và corruption, nhưng transportation audit cho thấy cách hiểu đó quá mạnh.

Các case train và nhiều subway case vượt 10 m vẫn nằm trong scale movement đã quan sát ở transportation-speed benchmark, trong khi phần lớn walk/bike case thì không. Vì vậy population >10 m là một mixture của nhiều nguyên nhân có thể có.

Kết luận chắc chắn hơn và hẹp hơn là: 10 m là bán kính mà bên dưới nó group đủ compact để collapse an toàn. Trên 10 m, within-second ordering không xác định nên vẫn phải break continuity một cách conservative, nhưng diagnostic nên gọi là spatial ambiguity thay vì khẳng định corruption.

Bài học tổng quát: một threshold có thể định nghĩa “khi nào phép transform an toàn” mà không hề phân loại bản chất dữ liệu thành đúng hay sai.

## 2026-09-18 — CP2 phải bắt đầu bằng abstention và timezone semantics, không phải một công thức Home/Office ngay lập tức

Shortcut hấp dẫn tiếp theo là lấy stay points, cộng 8 giờ rồi gọi location ban đêm là Home và location giờ hành chính là Office. EDA trước đã cho thấy cách đó không an toàn: GeoLife có trajectories ngoài Beijing trong khi timestamp PLT là UTC/GMT.

Vì vậy scaffold CP2 đặt timezone/geography gate trước semantic scoring. User có lịch sử quá ít cũng phải được phép abstain thay vì ép ra Home hoặc Office.

Một bài học khác là Home/Office là bài toán recurring location ở cấp user, không phải bài toán theo từng trajectory file. Notebook CP2 đầu tiên materialize 5,821 stays đã freeze, audit history sufficiency, rồi mới thử spatial clustering theo user trước khi định nghĩa score.

Home và Office cũng là inferred locations rất nhạy cảm. Vì vậy privacy trở thành một phần của artifact contract: precise user-level inferred coordinates chỉ nên nằm trong private cache; repo chỉ giữ aggregate diagnostics và decision records.

## 2026-09-18 — Materialization CP2 đầu tiên cho thấy vì sao cần abstention và cluster diagnostics

Run CP2 full-release đầu tiên reproduce chính xác frozen CP1 total: 5,821 stays trên 136 users. Đây là contract check quan trọng vì semantic stage giờ đã chứng minh là đang consume đúng behavior mà CP1 đã validate.

History support theo user rất không đều. Dù 120 users có ít nhất hai stays, chỉ 62 users có stays trên ít nhất mười ngày UTC khác nhau. Vì vậy Home/Office system phải có abstention và evidence threshold; ép label cho mọi user sẽ đánh đồng pipeline coverage với semantic certainty.

Thử nghiệm DBSCAN theo user cũng lộ ra một vấn đề clustering quan trọng. Với epsilon 200 m, khoảng cách lớn nhất từ median representative của cluster tới member stay đạt khoảng 527 m. DBSCAN epsilon giới hạn neighbor links theo density, không giới hạn total cluster diameter, nên chaining có thể tạo một “location” rộng hơn nhiều so với trực giác 200 m.

Điều này nghĩa là recurring-location contract cần compactness diagnostic rõ ràng hoặc một clustering rule khác trước khi freeze production semantics.

Spatial distribution của stays vẫn tập trung mạnh quanh Beijing nhưng có geographic outliers lớn. Kết quả thực nghiệm này xác nhận warning trước đó: không thể tạo local behavioral time bằng cách cộng 8 giờ cho mọi UTC timestamp.

## 2026-09-18 — Timezone scope phải gắn với observation, không chỉ với user

Timezone audit của CP2 làm lộ thêm một semantic issue nhỏ nhưng quan trọng. Một user có thể chủ yếu sống ở Beijing nhưng vẫn có travel stays ở nơi khác. Nếu chỉ classify user là “Beijing” rồi convert toàn bộ stays của user đó sang `Asia/Shanghai`, travel observations vẫn có thể bị gán sai local time.

Thiết kế v1 an toàn hơn là hai tầng:

1. quyết định user có đủ Beijing-focused hay không bằng sensitivity của stay-share và dwell-share;
2. ngay cả với user được accept, chỉ các stays nằm trong Beijing region mới đi vào semantic scoring theo local time.

Travel stays ngoài region bị exclude thay vì bị silently convert.

Bài học tổng quát cho spatiotemporal systems: metadata như timezone có thể cần scope ở cấp observation dù eligibility được quyết định ở cấp user.

## 2026-09-18 — Recurring-location clustering cần diameter contract, không chỉ neighbor radius

DBSCAN experiment đầu tiên cho thấy một mismatch quan trọng giữa trực giác về parameter và geometry thật. Dù epsilon là 200 m, một cluster vẫn có member cách median representative khoảng 527 m.

Đây không phải bug của DBSCAN; density connectivity có thể chain nhiều local links thành một component rộng hơn nhiều.

Với Home/Office inference, mình muốn spatial threshold có semantic trực tiếp: một recurring location không nên chứa các point có pairwise separation vượt threshold. Complete-linkage clustering phù hợp hơn vì mỗi merge được quyết định bởi maximum pairwise distance giữa hai nhóm.

Audit tiếp theo vì vậy so sánh complete linkage ở 100/200/300 m và verify exact cluster diameter trước khi freeze recurring-location contract.
