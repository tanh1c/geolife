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

## 2026-09-18 — Behavioral-time feature phải dùng interval overlap, không phải arrival-hour label

Scoring audit Home/Office đầu tiên dùng toàn bộ stay interval để đo evidence theo thời gian. Một stay từ 20:50 đến 21:30 chỉ nên đóng góp đoạn 21:00–21:30 vào night window. Nếu chỉ nhìn arrival hour rồi gán toàn bộ stay thì sẽ tạo boundary artifact.

Nguyên tắc này cũng áp dụng cho office evidence và các stay đi qua midnight. Behavioral-time feature là bài toán interval overlap, không phải point-in-time classification.

Mình cũng chưa biến score đầu tiên thành “probability”. Khi không có Home/Office ground truth, relevant-dwell share, số ngày support và margin top-1 so với top-2 là các evidence component dễ giải thích, nhưng không phải calibrated confidence probability. Bước tiếp theo là xem distribution và định nghĩa abstention rule trước khi productionize heuristic.

## 2026-09-18 — Home và Office không nên mặc định dùng chung threshold

Run scoring theo interval overlap đầu tiên cho thấy distribution evidence của Home và Office khác nhau khá rõ. Home candidate có median relevant-dwell share khoảng 0.635 và median top-two margin khoảng 0.513, trong khi Office chỉ khoảng 0.357 và 0.243.

Khác biệt này quan trọng. Một rule chung như “share >= 0.5” sẽ chỉ moderately selective với Home nhưng lại aggressive hơn nhiều với Office. Khi không có semantic ground truth, không có lý do để giả vờ rằng hai evidence family đã được calibrate trên cùng một scale.

Vì vậy bước tiếp theo là sensitivity riêng cho Home và Office. Ngoài coverage, mình cũng sẽ đo top location có giữ nguyên khi dịch time window một chút hay không; coverage ổn nhưng top location đổi liên tục vẫn là heuristic không ổn định.

## 2026-09-18 — Abstention gate cuối của CP2 đến từ stability + middle sensitivity, không phải pseudo-accuracy

Bounded scoring sensitivity giúp chốt stopping rule rõ ràng. Home window baseline 21–06 giữ nguyên top location cho 93.6% shared users khi so với 20–06 và 90.5% khi so với 22–06. Office baseline 09–17 cũng ổn định tương tự: 95.0% so với 08–17 và 92.5% so với 09–18.

Không có Home/Office ground truth nên không thể chọn threshold bằng cách “maximize accuracy”. CP2 v1 vì vậy freeze middle setting của support/share/margin: Home dùng 3 dates / 0.50 share / 0.20 margin; Office dùng 3 dates / 0.30 share / 0.10 margin. Hai gate này emit lần lượt 27 và 16 users trên semantic cohort 97 users.

Confidence cũng được gọi đúng nghĩa là evidence strength, không phải probability. Nó lấy trung bình dwell share, top-two margin và date-support factor saturate ở 5 dates, đồng thời vẫn expose toàn bộ raw components bên cạnh aggregate score.

## 2026-09-18 — RED tests bắt được zero-evidence dtype bug mà notebook full data không lộ ra

Production Home/Office implementation đầu tiên compile được nhưng fail RED tests khi một semantic evidence family hoàn toàn không có overlap. Sau merge với empty feature table, pandas giữ zero column ở object dtype; phép chia eager bên trong `np.where` sau đó ném `ZeroDivisionError`.

Full-release notebook có đủ mixture Home/Office evidence nên edge case này không tự nhiên xuất hiện.

Fix đúng không phải special-case test. Feature builder production giờ coercion dwell columns sang numeric và dùng `np.divide(..., where=denominator > 0)`, nhờ đó zero-evidence user trở thành abstention case bình thường.

Đây là ví dụ rất rõ vì sao chuyển từ notebook sang production vẫn cần acceptance tests dù exploratory output nhìn hoàn toàn hợp lý.

## 2026-09-18 — Full-release parity là contract check cuối giữa notebook và production

Production API `infer_home_office()` được chạy trên đúng cache 5,821 stays đã dùng trong CP2 notebook. Kết quả reproduce chính xác frozen emission counts: 27 HOME và 16 OFFICE, tổng 43 rows trên 36 users.

Parity check này khác unit tests: tests bảo vệ local semantics và edge cases, còn parity xác nhận assembled production path reproduce đúng quyết định notebook trên materialized dataset thật.

Khi cả hai cùng pass, handoff từ exploratory evidence sang production code của CP2 v1 mới thật sự kín.

## 2026-09-18 — Notebook nên lưu reasoning contract, không chỉ lưu code và output

Sau khi production parity đã pass, mình quay lại 02 / 02b / 02c / 03 để bổ sung narrative theo style mentor audit.

Một notebook reproducible nhưng chỉ có code vẫn chưa đủ cho handoff dài hạn. Người đọc cần biết:

- câu hỏi nào cell đang trả lời;
- vì sao metric đó tồn tại;
- output phải đọc theo denominator nào;
- conclusion nào được support;
- conclusion nào không được support;
- decision nào đã bị supersede bởi audit sau.

Điều này đặc biệt quan trọng với project này vì một số assumption ban đầu đã được sửa bằng evidence: blanket UTC+8 bị thay bằng geography/timezone cohort; DBSCAN 200 m bị thay bằng complete-link diameter contract; >10 m same-second không còn bị gọi là corruption.

Bài học: notebook tốt nên đóng vai trò decision record có thể chạy lại, không chỉ là scratchpad có biểu đồ.

## 2026-09-18 — Abstention là model output, không phải HTTP error

API contract đầu tiên làm rõ một boundary quan trọng giữa invalid request và valid uncertainty.

Timestamp malformed, coordinate ngoài domain hoặc interval đảo ngược là lỗi transport/schema nên trả HTTP 422. Nhưng user ngoài Beijing semantic cohort, không có recurring location, hoặc evidence Home/Office yếu vẫn là request hợp lệ. Các case này phải trả HTTP 200 với abstention reason rõ ràng.

Nhờ vậy serving semantics giữ đúng tinh thần conservative của CP2: uncertainty là first-class model output chứ không phải operational failure.

API v1 cũng không trả precise inferred Home/Office coordinates dù internal model có tính chúng. Chỉ trả request-local `location_id` cùng evidence fields giúp downstream đủ traceability mà giảm accidental semantic-location disclosure.

Một bài học khác: request-time configuration cũng là một phần của model contract. Nếu client được truyền threshold như `home_min_share`, một frozen CP2 model sẽ biến thành nhiều model variants theo từng request. Vì vậy v1 forbid extra tuning fields.

## 2026-09-18 — Full HTTP replay validate adapter semantics, không chỉ route availability

Release notebook của CP3 replay toàn bộ 136 users từ private cache 5,821 stays qua FastAPI endpoint rồi so response với direct `infer_home_office()`.

Aggregate counts match chính xác: 27 HOME và 16 OFFICE, tổng 43 emitted rows trên 36 users. Quan trọng hơn, notebook còn check exact emitted `(user_id, label)` keys, location ids, relevant dates và các numerical evidence fields.

Cách check này mạnh hơn chỉ nhìn aggregate count. Hai serving layers hoàn toàn có thể cùng cho 27/16 nhưng label nhầm những users khác nhau.

Replay cũng cho một observability table hữu ích về abstention. HOME abstain 39 geography cases, 24 recurring-history cases và 46 semantic-evidence cases; OFFICE có cùng hai count đầu và 57 semantic-evidence abstentions. Đây là model outcomes, không phải error rates.

Run này còn làm lộ pandas FutureWarning ở partial emission vì model concat một non-empty frame với một empty frame. Kết quả vẫn đúng nhưng warning cho thấy future dtype-risk. Production code giờ chỉ concat các non-empty frames và có regression test riêng.

## 2026-09-24 — Timezone là polygon lookup, không phải bán kính quanh một thành phố

Một review lại notebook 03 cho thấy tôi đã trộn hai khái niệm: **timezone assignment** và **Beijing-focused cohort selection**.

Rule hiện tại lấy một điểm tham chiếu gần trung tâm Beijing rồi dùng bán kính 100 km. Cách này có thể hữu ích như một engineering scope, nhưng nó không phải ranh giới timezone và cũng không phải ranh giới hành chính Beijing.

Điểm học được quan trọng hơn là timezone không nên được hiểu như một rectangle `lat_min / lat_max / lon_min / lon_max`. IANA tz database cung cấp timezone identifiers và representative locations; còn việc một GPS coordinate thuộc timezone nào là bài toán point-in-polygon. Các dataset như timezone-boundary-builder gắn mỗi polygon với một IANA `tzid`, và `timezonefinder` có thể lookup offline từ WGS84 `(lat, lon)`.

Thiết kế sạch hơn cho GeoLife là:

```text
stay coordinate
    ↓
timezone polygon lookup
    ↓
IANA tzid per stay
    ↓
ZoneInfo(tzid)
    ↓
local behavioral time
```

Sau đó mới xử lý một câu hỏi khác:

```text
user có Beijing-focused không?
```

Nếu cần cohort Beijing thật sự, nên dùng Beijing administrative polygon. Nếu chỉ cần một central-Beijing engineering cohort thì radius vẫn có thể dùng, nhưng phải gọi đúng tên và không diễn giải nó như timezone truth.

Bài học tổng quát: **geographic scope và timezone scope có thể liên quan nhưng không phải cùng một contract**. Khi phát hiện hai semantics đang bị gộp chung, nên tách chúng trước khi tune threshold.

## 2026-09-24 — Migration timezone nên thay một tầng logic mỗi lần

Notebook 03 đã được sửa để lookup IANA timezone theo từng stay thay vì dùng vòng tròn 100 km quanh một điểm Beijing.

Một điểm methodology quan trọng là **không retune mọi threshold cùng lúc**. Tôi giữ `80% stay share / 80% dwell share` như migration control:

```text
v1:
Beijing-distance proxy + 80/80

candidate:
coordinate timezone lookup + 80/80
```

Nhờ vậy nếu cohort hoặc HOME/OFFICE output thay đổi, nguyên nhân dễ quy về timezone assignment hơn thay vì bị trộn với threshold tuning.

Travel stays của user đủ điều kiện cũng không còn bị loại chỉ vì ở ngoài Beijing radius. Mỗi stay giữ IANA timezone riêng và được chuyển sang local wall time của chính nó.

Các con số v1 như 97 users, 4,197 semantic stays, 27 HOME và 16 OFFICE vì vậy chỉ còn là **historical reference**. Chúng không được copy sang candidate notebook như thể parity vẫn phải đúng.

Bài học: khi thay một upstream semantic contract, phải làm stale các downstream measured outputs và rerun chúng; giữ số cũ chỉ vì code phía sau chưa đổi sẽ tạo cảm giác reproducibility giả.

## 2026-09-24 — Nếu đề không yêu cầu geography scope thì timezone không nên trở thành filter

Run đầu của timezone-v2 cho thấy lookup theo coordinate hoạt động tốt: toàn bộ 5,821 stays đều xác định được IANA timezone, và phần lớn nằm trong Asia/Shanghai. Ban đầu tôi vẫn giữ rule 80/80 để chọn user "Asia/Shanghai-focused".

Review tiếp theo cho thấy đây vẫn là một restriction không cần thiết nếu bài toán chỉ yêu cầu Home/Office inference và không yêu cầu Beijing-only hay China-only.

Thiết kế cuối đơn giản hơn:

```text
mỗi stay
→ coordinate → timezone
→ UTC → local time của stay
→ recurring location
→ HOME/OFFICE evidence
```

Asia/Shanghai share vẫn có ích để mô tả dataset, nhưng không còn quyết định user có được vào pipeline hay không.

Bài học quan trọng: **metadata cần để diễn giải observation không nhất thiết phải trở thành cohort filter**. Timezone trả lời "đọc đồng hồ nào"; abstention nên đến từ evidence liên quan trực tiếp đến task như history, recurrence, share, margin và repeated dates.

## 2026-09-24 — DBSCAN eps tăng coverage nhưng không kiểm soát được diameter

Rerun cuối trên toàn bộ 5,821 timezone-resolved stays làm trade-off của DBSCAN rất rõ.

Khi eps tăng từ 10 m lên 200 m, số user có recurring location tăng từ 78 lên 104. Nhưng spatial compactness xấu đi nhanh:

```text
eps 30m  → 90 recurring users, 0 clusters >200m, max diameter ~181m
eps 50m  → 94 recurring users, 6 clusters >200m, max ~249m
eps 100m → 97 recurring users, 24 clusters >200m, max ~441m
eps 200m → 104 recurring users, 86 clusters >200m, max ~837m
```

Một lesson quan trọng là `eps=200m` chỉ giới hạn neighbor connectivity, không giới hạn cluster diameter. Chaining có thể nối nhiều bước ngắn thành một recurring location rất rộng.

Vì vậy không nên chọn DBSCAN eps chỉ bằng coverage. Nếu muốn threshold có semantics trực tiếp kiểu "location diameter <= X", complete-link phù hợp hơn cho contract này.

## 2026-09-26 — 03a: structure không đồng nhất quan trọng hơn giả định Home/Office đơn giản

Behavior-first EDA 03a được đóng như evidence checkpoint, không phải redesign production. Trong 136 users có CP1 stay, anchor distribution là 19 dominant, 13 two-anchor, 72 multiple-anchor và 32 no-stable-anchor. Vì vậy phần lớn stay-users không khớp trực tiếp với worldview đơn giản `HOME anchor → OFFICE anchor`.

Schedule evidence lại là negative result hữu ích. Dù 46 users đủ support, within-user weekly JSD median là 1.000 (IQR 0.652–1.000), không thấp hơn between-user 0.904 hay shuffled-week null 1.000. Metric hiện tại chưa chứng minh personalized schedule structure; không nên thay 09–17 bằng per-user hours chỉ dựa vào JSD.

Signal đáng đào tiếp là 23 mobile-work-like candidates: cả 23 có multiple anchors, cả 23 bị frozen OFFICE abstain, và không ai OFFICE emitted. Điều này không xác nhận nghề nghiệp hay semantic WORK, nhưng là hypothesis rõ ràng rằng fixed-office baseline có thể bỏ sót một distributed-mobility regime. 03b phải kiểm tra bằng evidence độc lập như mode labels, route/transition recurrence, weekday-weekend contrast, sensitivity và negative controls, không dùng lại wrapper features để tự chứng minh wrapper.

## 2026-09-27 — Audit code phải tách “chạy được” khỏi “đủ làm evidence”

03b cho thấy một script chạy được chưa có nghĩa output đã đủ chất lượng để dùng làm evidence. Hai lỗi thiết kế ban đầu rất điển hình:

1. transportation summary dùng thời lượng label window thay vì movement segments đã qua frozen cleaning;
2. sensitivity giữ nguyên candidate cohort thay vì thực sự rerun candidate wrapper.

Bản continuation sửa hai điểm này trước khi đọc kết quả. Bài học là validation pipeline cần kiểm tra **provenance của evidence** và **rerun đúng causal dependency** chứ không chỉ kiểm tra code không lỗi.

Các thay đổi hiện chỉ là engineering hardening; chưa có kết luận behavior mới cho tới khi full-release run và verification pass.

## 2026-09-28 — Symlink có thể phá privacy guard dựa trên resolved path

Modal runner đầu tiên symlink `artifacts/03a` sang persistent Volume. Cách này nhìn hợp lý về execution nhưng 03a privacy guard dùng `Path.resolve()`, nên path sau resolve không còn chứa `artifacts/03a` và bị reject.

Cách sửa tốt hơn là không làm yếu guard và không dùng symlink. Runner truyền cache root rõ ràng qua environment, cập nhật approved private root của module rồi truyền explicit `stay_cache` / `point_day_cache` vào materialization.

Bài học: persistence layer không nên thay đổi semantic của privacy/path invariants. Nếu guard kiểm tra resolved path, symlink là một phần của threat model chứ không chỉ là filesystem convenience.

## 2026-09-29 — DBSCAN không chỉ có eps; MinPts cũng là modeling assumption

Notebook 03 đã audit `eps` khá kỹ nhưng vẫn cố định `min_samples=1`. Đây là một assumption đáng test.

Với scikit-learn DBSCAN, `min_samples` là số samples trong epsilon-neighborhood để một point được coi là core point, tính cả chính point đó. Vì vậy:

```text
min_samples = 1
→ mọi point tự nó là core
→ không có noise theo density
→ isolated stay thành singleton cluster
→ chaining permissive hơn

min_samples tăng
→ cần local density mạnh hơn
→ có thể loại transient/sparse stays thành noise
→ nhưng cũng có thể làm mất recurring places hợp lệ của user ít dữ liệu
```

Điểm quan trọng: downstream hiện đã có rule recurring location `>=2 stays`, nhưng điều đó **không tương đương** với `min_samples=2`. MinPts kiểm tra local epsilon-neighborhood density, còn recurring rule kiểm tra tổng visits sau clustering.

Vì vậy cần sensitivity riêng `min_samples=1/2/3/5`, tốt nhất kết hợp với representative eps values, trước khi nói DBSCAN configuration có lý do đầy đủ.

## 2026-09-29 — Support matching phải dùng đúng schema đã freeze

03b từng dùng `observed_span_h` để match/support-balance vì field này tồn tại ở point-day layer trong design, nhưng frozen 03a user feature table không export nó. Full audit vì vậy fail dù unit tests synthetic vẫn pass.

Bài học:

- audit downstream phải kiểm tra schema thật từ upstream artifact, không suy ra field chỉ từ design/spec;
- test fixture nên phản ánh frozen upstream schema, không thêm convenience fields mà production table không có;
- với support balance, dùng các field thật sự đã freeze: `active_days`, `usable_temporal_days`, `usable_active_days`, `cp1_stay_count`.

Ngoài ra, verification gate phải phân biệt lỗi của change hiện tại với technical debt sẵn có. Full pytest vẫn có giá trị regression, nhưng Ruff cho 03b nên target file 03b thay vì fail vì notebook lint cũ không liên quan.

## 2026-09-29 — Robust candidate set chưa đồng nghĩa semantic regime đã được validate

03b cho một ví dụ rõ về khác biệt giữa **robustness** và **semantic validation**.

Candidate set 23 users cực kỳ ổn định: anchor threshold 100/200/300 m đều giữ nguyên 23 users; thay mobility threshold ±10% chỉ thêm/bớt 1 user; support ±1 weekday không đổi cohort.

Tuy nhiên independent evidence chưa đủ mạnh:

- A/B aggregate observation support vẫn lệch đáng kể dù đã match đủ 23 cặp;
- transportation labels chỉ phủ 6/23 A users, 12/23 B users và 3/16 C users;
- motorized share của A/B/C khá giống nhau;
- median recurrent route edges của A và B đều bằng 0;
- A có nhiều transitions và edge entropy cao hơn, nhưng điều đó mô tả mobility complexity chứ chưa chứng minh work semantics.

Bài học: một wrapper có membership stability rất cao chỉ cho thấy definition ổn định quanh các threshold đã thử. Nó không tự tạo ra external/independent semantic evidence. Vì vậy decision đúng là `mixed evidence`, không phải `supported work regime`.

## 2026-09-29 — Khi matched users vẫn lệch exposure, cần control ở user-day level

03b match đủ 23 cặp A/B nhưng aggregate support vẫn lệch lớn. Điều này cho thấy user-level matching chưa chắc đã loại được observation confounding.

03b.1 chuyển control xuống user-day level:

```text
mỗi A/B pair
→ tách weekday/weekend
→ lấy min usable days ở mỗi stratum
→ downsample phía có nhiều ngày hơn
→ recompute metric
→ lặp bootstrap
```

Route analysis dùng riêng `usable_for_motif` days. Transportation subset control theo matched labeled hours. Cách này trả lời câu hẹp hơn: khác biệt A/B có còn khi hai phía được quan sát với lượng exposure tương đương hay không?

Bài học: normalization kiểu km/day hữu ích nhưng chưa đủ khi số ngày quan sát và cấu trúc ngày quan sát lệch mạnh. Pairwise exposure control giúp test trực tiếp confounding đó.

## 2026-09-29 — Merge schema collision có thể ẩn sau preflight synthetic

03b.1 fail vì cả `clustered` và daily eligibility table đều có `local_weekday`. Merge theo `user_id + local_date` khiến pandas tạo `local_weekday_x/y`, nhưng code vẫn gọi `local_weekday`.

Fix tốt hơn không phải chọn một suffix, mà là giảm merge về đúng mục đích: daily table chỉ dùng để gate `usable_for_motif`, nên chỉ cần `user_id + local_date`. Weekday có thể derive deterministic từ `local_date`.

Bài học: khi một merge chỉ nhằm lọc eligibility, đừng mang theo columns không cần thiết. Narrow join schema giảm collision và làm provenance rõ hơn.

## 2026-09-29 — Bootstrap đúng nhưng implementation pandas-naive có thể làm experiment không thực dụng

03b.1 ban đầu đúng về ý tưởng nhưng chậm vì mỗi bootstrap lại filter/copy DataFrame và transport còn iterate `iloc` theo segment. Với 23 cặp × 500 repetitions, overhead pandas lặp lại lớn hơn bản thân thống kê cần tính.

Fix giữ nguyên experiment nhưng thay execution:

- filter A/B pair một lần ngoài loop;
- sample trên pair-local frames;
- transport convert sang NumPy arrays một lần/user;
- dùng permutation + cumulative duration vectorized để đạt exact matched hours;
- log progress theo stage/pair.

Bài học: reproducibility không chỉ là deterministic output; long-running audit cũng cần progress observability và implementation đủ rẻ để rerun được.

## 2026-09-29 — Exposure-controlled 03b.1 result

Sau khi equalize usable-day exposure trong từng A/B pair, Group A vẫn có movement magnitude cao hơn: khoảng +22.9 km/day cleaned distance và +0.74 h/day movement proxy.

Route evidence hẹp hơn: edge entropy cao hơn khoảng 0.232 với 95% bootstrap interval trên 0, nhưng recurrent-edge difference bằng 0 và transition/day cùng distinct-edge/day có interval chạm 0.

Kết luận phù hợp: observation imbalance không giải thích hết behavioral difference, nhưng evidence hiện tại chỉ support một descriptive mobility-complexity cohort. Không thay đổi Home/Office semantics từ kết quả này.

## 2026-09-29 — Mentor demo nên kể lại reasoning, không chỉ dump chart

Sau 03a → 03b → 03b.1, số lượng runner/report đã đủ nhiều để khó demo trực tiếp. Vì vậy tạo một notebook narrative riêng, reuse cache đã validate thay vì rerun raw data.

Notebook mentor-facing đi theo format:

```text
câu hỏi
→ vì sao cần kiểm tra
→ cách đo
→ kết quả
→ không được suy ra gì
→ decision
```

Cách này giúp phân biệt rõ research finding với semantic claim. Ví dụ 23-user cohort được trình bày là robust mobility-complexity cohort, đồng thời notebook giải thích vì sao recurrent-route evidence và transport coverage chưa đủ để gọi nó là mobile-work.

Bài học: reproducibility notebook và communication notebook có mục tiêu khác nhau. Runner cần auditability; mentor notebook cần giữ provenance nhưng tối ưu cho reasoning và decision trace.

## 2026-09-29 — Case maps nên minh họa aggregate finding, không thay thế aggregate finding

Mentor demo dễ hiểu hơn khi có spatial cases thật thay vì chỉ bảng aggregate. Nhưng nếu chọn case bằng mắt thì rất dễ cherry-pick.

03c visual v2 vì vậy chọn case deterministic: archetype user gần median active-days của class; A/B pair dùng candidate có edge entropy gần median Group A rồi lấy đúng matched control.

Map hiển thị raw GeoLife user ID, cached CP1 stays, L* recurring locations và chronological stay path. Daily timeline và L* transition heatmap giúp nối intuition với 03b/03b.1.

Bài học: case visualization nên trả lời “pattern này trông như thế nào?”; câu “pattern có tồn tại ở population không?” vẫn phải dựa vào sensitivity, matched controls và bootstrap exposure control.

## 2026-09-29 — Demo notebook không nên giả định derived cache luôn tồn tại

03c mentor demo fail vì mình giả định `03a/summary.json` luôn có trên Modal Volume. Thực tế 03b có thể reuse `stays_baseline_v1.pkl` và `cleaned_point_daily_metrics.pkl` mà không chạy/persist toàn bộ output 03a.

Fix tốt hơn là tách cache thành hai tầng:

```text
frozen expensive inputs
= stays + point-day metrics

cheap derived demo artifacts
= summary + user features + audit tables
```

Nếu derived layer thiếu, notebook rebuild từ frozen inputs thay vì scan raw trajectories. Như vậy demo notebook vừa self-contained hơn vừa giữ runtime hợp lý.

## 2026-09-29 — Clone repo chưa đồng nghĩa package đã import được

03c trên fresh Modal runtime clone repo thành công nhưng fail khi import `analysis/03a...` vì module đó import package `geolife`, trong khi project chưa được editable-install và `src/` chưa nằm trong Python path.

Bài học: notebook runtime setup phải theo thứ tự `checkout -> install project -> add import paths -> import analysis helpers`. Việc file source tồn tại dưới `/tmp/geolife` không tự làm `src/geolife` trở thành importable package.



## 2026-10-01 — Tăng DBSCAN MinPts không sửa được chaining

Notebook 04 kiểm tra trực tiếp giả định còn thiếu của DBSCAN: `min_samples = 1/2/3/5` trên cùng 97-user semantic cohort.

Kết quả quan trọng nhất ở `eps=200 m`:

```text
min_samples=1
→ 73 recurring users
→ 418 recurring locations
→ 585 singleton locations
→ max diameter ~836.66 m

min_samples=2
→ vẫn 73 recurring users
→ vẫn 418 recurring locations
→ 585 singleton stays chuyển thành noise
→ max diameter vẫn ~836.66 m

min_samples=3/5
→ recurring-user coverage giảm còn 64/56
→ max diameter vẫn ~836.66 m
```

Trong khi frozen complete-link 200 m giữ cùng 73 recurring users nhưng có 486 recurring locations, p95 recurring diameter ~180.95 m, max ~199.23 m và không có recurring cluster nào vượt 200 m.

Bài học:

- `min_samples=2` không tương đương với downstream rule `stay_count >= 2`; trong run này nó chủ yếu loại singleton thành noise;
- tăng MinPts có thể giảm coverage trước khi nó giải quyết được representation problem;
- DBSCAN `eps` + MinPts vẫn không tạo hard maximum-diameter contract vì chaining là thuộc tính của density connectivity;
- user coverage giống nhau không có nghĩa spatial representation tương đương.

Decision hợp lý vẫn là giữ complete-link 200 m cho semantic Home/Office work. Đây là robustness/engineering evidence, không phải accuracy claim vì GeoLife không có Home/Office ground truth.

Scope cần giữ rõ: follow-up này chạy trên 97-user semantic cohort, không thay thế full-stay DBSCAN audit và không revalidate trực tiếp các anchor counts của behavior EDA trên 136 users.


## 2026-10-01 — Bài học từ related work: đánh giá HOME/OFFICE không nhất thiết cần POI

### Andrade, Cancela & Gama (2019) — meaningful places và DBSCAN chaining

Paper Mining Human Mobility Data to Discover Locations and Habits xây meaningful places từ stay points và recurrence mà không cần external semantic source. Trong experiment GeoLife, họ dùng 200 m / 20 phút cho stay point; với user 004, 2.437 stay points được gom thành 50 meaningful places và hai place có tần suất cao nhất được diễn giải thành Home/Work. Paper cũng chỉ ra một nhược điểm đúng với audit của project: DBSCAN có thể tạo cluster dài do density-connected chaining.

Lesson cho GeoLife project:

- semantic map/POI không phải điều kiện bắt buộc để khai phá recurrent anchors;
- compactness của location và recurrence của visit/movement là evidence độc lập cần giữ;
- user 004 chỉ là sanity reference của paper, không phải ground truth cho toàn dataset;
- kết quả Stage 04 giữ complete-link 200 m có support phương pháp luận mạnh hơn sau khi đối chiếu cảnh báo chaining này.

### Dong et al. (2022) — threshold không phải classifier

Paper The universality in urban commuting across and within cities dùng 200 m / 10 phút để detect stay, DBSCAN MinPoint=1 để tạo stay locations, nhưng HOME/WORK cuối cùng được phân loại bằng XGBoost với 28 features và self-reported ground truth. Feature set gồm support ở cấp user, weekday/weekend, daytime/nighttime ratios, location shares, transfer-matrix counts và POI residential/work counts.

Lesson:

- không được hiểu 200 m + recurring là đủ để suy ra HOME/OFFICE;
- transition structure, recurrence và observation support là các trục evidence riêng;
- POI chỉ là một phần nhỏ của feature design, không phải toàn bộ validation;
- accuracy 94.1% HOME / 93.0% WORK của paper gắn với supervised labels của dataset họ, không được transfer sang GeoLife.

### HoWDe (2025) — coverage và semantic selection phải tách nhau

HoWDe biến stop sequences thành hourly bins, lọc day theo temporal coverage, dùng tỷ lệ observed hours thay vì raw absolute time, dùng sliding windows và cho phép not detected. Paper đánh giá đồng thời detected accuracy và fraction-not-detected, tức accuracy/retention là trade-off chứ không phải cứ emit nhiều là tốt hơn.

Lesson:

- support gate và semantic score nên là hai khái niệm tách biệt;
- abstention là output hợp lệ;
- proportion trên observed data phù hợp hơn raw count khi sampling không đều;
- sliding window là hướng follow-up hợp lý nếu static assignment không ổn định;
- HoWDe cũng nói rõ giới hạn: temporal pattern không tự suy ra semantic purpose chi tiết và một run chưa trực tiếp giải quyết rotating night-shift lifestyles.

### Quyết định áp dụng

Stage 05 pivot từ POI lookup sang reliability validation:

recurring locations -> multiple semantic rankers -> split-half -> held-out -> dropout -> cross-method agreement -> schedule-sensitivity

Frozen 27 HOME / 16 OFFICE chỉ còn là parity comparator. Candidate coverage mới được phép lớn hơn, nhưng không method nào được coi là truth cho tới khi qua các reliability axes.


## 2026-10-01 — HOME ổn định hơn OFFICE; coverage lớn hơn không đồng nghĩa semantic tốt hơn

Stage 05 xác nhận frozen parity 27 HOME / 16 OFFICE, nhưng khi bỏ final emission gate thì fixed-window đã có 35 HOME và 27 OFFICE candidates. Recurrence ranker còn có thể xếp 73 HOME candidates và 31 OFFICE candidates. Vì vậy 27/16 là kết quả của conservative emission policy, không phải trần tự nhiên của dữ liệu.

Điểm quan trọng hơn là agreement khác nhau rõ giữa HOME và OFFICE.

HOME:

- fixed vs HoWDe-style cùng location 18/19 = 94.7%;
- fixed vs recurrence 29/35 = 82.9%;
- HoWDe-style vs recurrence 17/20 = 85.0%.

OFFICE:

- fixed vs HoWDe-style vẫn khá cao 13/16 = 81.3%;
- nhưng fixed vs recurrence chỉ 7/22 = 31.8%;
- HoWDe-style vs recurrence chỉ 3/20 = 15.0%.

Bài học:

- HOME có một recurrent dominant-anchor signal khá mạnh, nên nhiều assumptions khác nhau vẫn hội tụ về cùng location;
- OFFICE phụ thuộc mạnh hơn vào temporal semantics — recurrence của một anchor ban ngày chưa đủ để gọi nó là workplace;
- emit nhiều hơn không phải là bằng chứng tốt hơn; recurrence HOME có coverage 73 users nhưng held-out top-1 chỉ ~43.3%;
- reliability phải đọc cùng coverage, không đọc riêng từng cột.

Missing-data stress cũng cho thấy fixed HOME tương đối bền: khi bỏ ngẫu nhiên 30% stays, retention vẫn ~84.8%; recurrence HOME ~87.2%. HoWDe-style giảm còn ~68.3%, cho thấy proportional hourly design hiện tại nhạy hơn với sparse stop support trong GeoLife.

## 2026-10-01 — Time-shift là stress test của assumption, không phải accuracy test

Dịch toàn bộ local timestamps +12 h nhưng giữ nguyên physical locations tạo ra một metamorphic test hữu ích:

- recurrence HOME giữ 100% candidate;
- recurrence OFFICE giữ ~77.4%;
- fixed HOME chỉ giữ ~37.1%, fixed OFFICE ~14.8%;
- HoWDe-style HOME/OFFICE giữ ~25.0% / ~14.3%.

Không nên diễn giải rằng recurrence vì thế "đúng hơn". Fixed-window và HoWDe-style cố ý dùng clock windows, nên sensitivity là thuộc tính thiết kế.

Bài học đúng là:

- +12 h test đo schedule dependence;
- HOME physical-anchor evidence có thể tách phần recurrence khỏi phần circadian interpretation;
- OFFICE cần adaptive/sliding-window reasoning nếu muốn hỗ trợ atypical schedules;
- một global time window không nên được mở rộng chỉ vì muốn tăng coverage.

Quyết định tiếp theo: xây consensus/support tiers cho HOME và sliding-window/adaptive audit cho các OFFICE/WORK assignments không ổn định, thay vì thay production rule ngay.

## 2026-10-01 — Consensus tier nên tổng hợp evidence axes, không cộng raw score

Ba HOME ranker dùng score có ý nghĩa khác nhau:

- fixed-window dùng dwell share trong frozen time window;
- HoWDe-style dùng observed-hour / visited-day proportions;
- recurrence dùng dwell/recurrence ranking.

Vì vậy không nên normalize rồi cộng score để tạo một confidence giả.

Stage 05b giữ riêng:

```text
method convergence
split consistency
held-out top-1
30% dropout robustness
```

sau đó chỉ dùng rule minh bạch để tạo HIGH / MEDIUM / UNCERTAIN.

Bài học: khi nhiều weak labelers không cùng thang đo, consensus nên dựa vào agreement + independent validation axes thay vì arithmetic score fusion. Tier cũng chỉ là audit evidence, không phải calibrated probability.

## 2026-10-01 — Adaptive WORK nên chọn anchor trước, đo clock behavior sau

Stage 05 cho thấy OFFICE phụ thuộc mạnh vào temporal assumptions. 05b vì vậy không tạo candidate bằng một khung giờ mới.

Flow mới:

```text
reliable HOME
→ exclude HOME
→ sliding windows
→ recurring secondary anchor
→ persistence / switches
→ arrival-hour center & concentration
```

Clock pattern được đo sau khi chọn secondary anchor. Điều này cho phép thấy một anchor ổn định nhưng có schedule lệch hoặc thay đổi mà không loại nó ngay từ đầu bằng 09–17.

Bài học: nếu chính time window là hypothesis cần kiểm tra, đừng dùng cùng time window để construct candidate rồi lại dùng candidate đó để validate time window.

## 2026-10-01 — Timezone-aware data cần timezone-aware audit windows

Synthetic execution của 05b bắt được lỗi mà syntax-check không thể thấy: `arrival_time_local` là timezone-aware nhưng window boundaries ban đầu được tạo từ Python date nên timezone-naive.

Fix:

```text
min/max arrival_time_local
→ normalize()
→ pd.date_range()
```

như vậy sliding windows giữ đúng timezone của semantic stays.

Bài học: notebook research code cần ít nhất một executable synthetic path; syntax-valid không đảm bảo datetime semantics đúng.

## 2026-10-01 — Consensus mạnh làm co lại expansion: 73 recurring HOME candidates chỉ còn 2 case mới đáng review

Stage 05 cho thấy recurrence có thể rank HOME cho 73 users, nhưng Stage 05b buộc candidate phải qua method convergence và reliability axes.

Kết quả winner: HIGH 21, MEDIUM 4, UNCERTAIN 42.

Trong 25 HIGH/MEDIUM winners:
- 23 đã là production HOME;
- chỉ 2 chưa emit;
- cả 2 vẫn là fixed-window HOME candidates, chỉ fail final share/margin emission gate;
- không có HIGH/MEDIUM winner nào xuất phát từ tập outside-fixed-candidate rộng hơn.

Bài học: coverage exploration rất hữu ích để tìm trần candidate, nhưng multi-axis reliability có thể thu hẹp mạnh phần thật sự đáng mở rộng. Một phương pháp recurrence có coverage cao không đồng nghĩa production nên tăng 27 HOME lên gần 73.

Ngoài ra, 23/27 production HOME emissions xuất hiện như HIGH/MEDIUM unique consensus winners. Bốn emission còn lại không nên gọi là sai; chúng chỉ có convergent evidence yếu hơn dưới audit hiện tại.

## 2026-10-01 — Sliding-window secondary anchor tìm được persistence, nhưng chưa tìm được WORK semantics

Trong 25 user có HOME HIGH/MEDIUM, primary 42-day audit cho 9 stable secondary anchor, 3 multi-anchor, 1 unstable và 12 insufficient.

Vấn đề đầu tiên là support: gần một nửa cohort không đủ evidence cho primary window.

Vấn đề thứ hai là semantic convergence. Dominant adaptive anchor chỉ match fixed OFFICE 40.0%, HoWDe-style OFFICE 28.6%, và recurrence OFFICE 54.5%.

Do đó persistence của một non-HOME anchor là behavioral evidence thật, nhưng chưa đủ để gọi nó là workplace.

Sensitivity ở threshold 0.70: 28d -> 10 sufficient / 6 stable; 42d -> 13 / 9; 56d -> 14 / 10.

Window dài hơn chủ yếu tăng usable support. 42d và 56d không tạo semantic breakthrough; agreement với fixed OFFICE vẫn quanh 40%.

Bài học: khi window length tăng, phải tách hai hiệu ứng: more observation support vs better semantic identification. Không được coi stable-count tăng là accuracy tăng.

Decision: nếu tiếp tục WORK, chỉ audit subset stable-secondary bằng transition/weekday/arrival evidence độc lập. Không tune một threshold persistence khác rồi tự gọi nó là OFFICE.


## 2026-10-01 — Khi candidate đã được chọn bằng recurrence, validation tiếp theo phải dùng evidence khác

05b chọn stable secondary anchor dựa chủ yếu vào persistence / recurrence qua sliding windows. Nếu 05c lại dùng active-day share hoặc dominant-window share để xác nhận, đó chỉ là self-validation.

Thiết kế 05c chuyển sang bốn trục khác:

- weekday-weekend contrast;
- direct HOME ↔ secondary transition regularity;
- arrival-time concentration;
- dwell-duration regularity.

Bài học: candidate construction và validation nên tách feature càng nhiều càng tốt. Trong dữ liệu không có ground truth, việc dùng cùng feature để tạo candidate rồi dùng lại feature đó làm validation rất dễ tạo confidence giả.

## 2026-10-01 — Same-user peers tốt hơn một threshold toàn cục cho audit nhỏ

Subset 05c chỉ có 9 stable-secondary users. Với N nhỏ và user heterogeneity lớn, đặt thêm một rule kiểu arrival concentration > X hay weekday share > Y sẽ rất tùy ý.

05c vì vậy hỏi:

candidate này có nổi bật hơn các recurring non-HOME anchors khác của chính user không?

Output là within-user percentile, top-1 axis, và candidate-minus-peer-median.

Bài học: với mobility behavior cá nhân hóa mạnh, relative within-user evidence thường phù hợp hơn một global cutoff mới. Nhưng cần ít nhất một peer đủ support; nếu không top-1 chỉ là kết quả vacuous.

## 2026-10-01 — Persistence của secondary anchor không đồng nghĩa commute-like regularity hội tụ

05c kiểm tra 9 stable-secondary users từ 05b bằng evidence khác với rule chọn candidate. Chỉ 7 users có ít nhất một recurring non-HOME peer đủ support để so sánh công bằng.

Kết quả primary:

- weekday-weekend contrast: 5/7 candidate đứng top-1;
- HOME<->secondary transition-day share: 3/7 top-1;
- arrival-time concentration: 0/7 top-1;
- dwell-duration regularity: 0/7 top-1.

Quan trọng nhất: không user nào đứng top-1 trên >=3/4 axes. Chỉ 1 user đạt 2 axes; 6 users chỉ đạt 0-1 axis.

Bootstrap candidate-minus-peer-median cho cả bốn metrics đều có 95% interval cắt 0. Weekday contrast và HOME-pair transition có hướng dương, nhưng N=7 quá nhỏ và evidence không hội tụ.

Bài học: persistence qua sliding windows là một property riêng. Nó không tự kéo theo arrival regularity, dwell regularity hay transition dominance. Vì vậy stable_secondary_anchor nên giữ là behavioral state, không nâng thành OFFICE.

## 2026-10-01 — Related-work nên được áp dụng theo trạng thái hiện tại của project, không theo kiến trúc greenfield

Deep-research report đề xuất Trackintel làm backbone, HoWDe làm robust HOME/WORK estimator, rồi habit/change-detection downstream. Kiến trúc đó hợp lý nếu bắt đầu mới, nhưng project hiện đã audit sâu CP1 cleaning/stays và complete-link locations.

Áp dụng hợp lý lúc này:

- không thay frozen CP1/CP2 bằng Trackintel;
- có thể dùng Trackintel như external comparator và tracking-quality reference;
- formalize coverage-before-change-detection;
- chuyển trọng tâm sang meaningful routines / OD habits / behavior change, vì các bài toán này không cần ép secondary anchor thành WORK;
- dùng commute distance, OD entropy, transition/mode change như supporting evidence;
- nếu dùng change-detection repo thì refactor/test như research algorithm, không copy default parameter rồi coi là truth.

Bài học tổng quát: literature integration phải tôn trọng accumulated validation debt. Một thư viện tốt không tự động đáng để thay một pipeline đã được audit nếu việc thay đó làm mất toàn bộ comparability của các experiment trước.


## 2026-10-01 — Routine nên được biểu diễn bằng OD + thời gian, không cần semantic WORK

Sau 05c, việc cố xác nhận secondary anchor là OFFICE không còn tạo thêm evidence mạnh. Stage 06 đổi đơn vị phân tích từ semantic place sang behavioral routine:

```text
supported daily sequence
→ directed OD edge
→ recurrence
→ local departure-time habit
```

Bài học:

- một OD pair có thể lặp ổn định dù whole-day motif thay đổi vì thêm/bớt một stop;
- exact motif là comparator strict, không nên là representation duy nhất;
- recurrence và clock regularity phải giữ thành hai axes riêng, không cộng thành pseudo-confidence;
- giờ trong ngày là cyclic: 23:30 và 00:30 phải gần nhau, vì vậy mean/concentration tuyến tính thông thường là không phù hợp;
- sequence order nên dùng UTC timestamp, còn departure habit dùng local clock;
- support gate phải chạy trước routine mining để missing observation không biến thành behavioral absence.

Với edge có đủ transitions, Stage 06 thử 1–3 departure-time modes sau circular unwrapping và dùng BIC để mô tả multimodality. Số mode chỉ là temporal pattern, không phải loại nghề hay trip purpose.

Nếu routine coverage và split-half stability đủ tốt, representation này mới phù hợp để Stage 07 detect behavior change.

## 2026-10-01 — Import được source tree không có nghĩa runtime dependencies đã đầy đủ

Stage 06 trên Modal gặp case:

`geolife` import được từ `/tmp/geolife/src`, nhưng `timezonefinder` chưa được cài.

Setup cũ chỉ chạy `pip install -e .` khi `geolife` import fail, nên dependency path bị skip và `resolve_stay_timezones()` mới fail ở cell sau.

Bài học:

- notebook setup phải check các optional/runtime dependencies mà helper thực sự cần, không chỉ check package chính có import được hay không;
- source path trên `sys.path` có thể làm package chính import thành công dù environment chưa được install đầy đủ;
- dependency check nên idempotent: thiếu thì cài, có rồi thì skip.

Stage 06 hiện check `timezonefinder==9.0.0` trực tiếp trước khi import helper 03a.


## 2026-10-01 — Top-1 instability không đồng nghĩa distribution instability

Stage 06 chỉ có 6/45 users giữ cùng dominant OD qua first/second half. Nhưng top-1 là statistic rất giòn: hai edge 40%/38% có thể đổi rank thành 38%/40% dù behavior distribution gần như giữ nguyên.

Stage 06b vì vậy chuyển primary stability evidence sang:

- Jensen-Shannon divergence;
- weighted Jaccard;
- total variation;
- top-3 overlap.

Bài học: trước khi gọi một rank swap là behavioral change, phải kiểm tra toàn distribution.

## 2026-10-01 — Change detection cần null model cho sampling variability

Sparse observation có thể làm first/second halves khác nhau ngay cả khi không có temporal change thật.

06b tạo null trực tiếp trong từng user:

```text
chronological split
vs
200 random balanced partitions
```

Nếu chronological JSD không lớn hơn random partitions, instability có thể đến từ support/sampling. Nếu nó vượt random p95, ta mới có drift-like evidence đáng mang sang Stage 07.

Đây vẫn không phải ground-truth event; nó chỉ tách temporal ordering khỏi sampling-only variability tốt hơn.

## 2026-10-01 — High circular concentration với N=2 chưa phải strong routine

Stage 06 có median departure concentration cao nhưng nhiều repeated edges chỉ xuất hiện hai ngày. Hai giờ departure gần nhau có thể tạo concentration gần 1 mà uncertainty vẫn rất lớn.

06b bootstrap ở cấp active day:

```text
one circular mean / edge-day
→ resample days
→ concentration CI
```

Do đó support count và lower confidence bound được đọc cùng point estimate.

## 2026-10-01 — GMM multimodality cần evidence ngoài BIC

Stage 06 permissive GMM chỉ có 11 modeled edges từ 2 users, nhưng 8 edge chọn 3 components. Đây là pattern dễ over-interpret khi N nhỏ.

06b chỉ gọi strict multimodal khi đồng thời có:

- >=5 active days;
- >=8 transitions;
- ΔBIC >=10 so với 1 mode;
- mọi component weight >=0.20;
- center separation >=2 giờ.

Bài học: model selection criterion không thay thế minimum support và component interpretability checks.

## 2026-10-01 — JSD rất cao không có nghĩa temporal drift nếu random split cũng cao như vậy

06b cho kết quả tưởng như rất bất ổn:

- 45 users có edge distribution ở cả hai halves;
- median chronological JSD = 1.0;
- weighted Jaccard median = 0;
- top-3 overlap median = 0.

Nếu chỉ nhìn chronological split, rất dễ kết luận behavior thay đổi mạnh.

Nhưng random balanced partitions của chính các supported days cũng cho median JSD = 1.0. Chỉ 2/45 users có chronological JSD vượt random p95.

Bài học:

```text
high chronological difference
≠ temporal change

high chronological difference
+ equally high random-partition difference
≈ sparse representation / sampling instability
```

Đây là lý do null model theo từng user quan trọng trước change detection.

## 2026-10-01 — Exact OD identity đang quá sparse cho population-level change detection

Support tiers co rất nhanh:

```text
>=2 active days → 23 users
>=3 active days →  9 users
>=5 active days →  2 users
```

Departure-time regularity của strong edges khá tốt (median concentration ~0.964; median bootstrap lower bound ~0.944), nhưng 12 strong edges chỉ đến từ 2 users.

Strict multimodality còn hẹp hơn: 6 modeled edges từ 1 user, 1 strict multimodal edge.

Bài học: một feature có thể rất stable conditional on strong support nhưng vẫn không đủ population coverage để làm backbone cho detector.

## 2026-10-01 — Motif comparator phải phân biệt stationary repeated days với mobility routines

Primary 06b comparator cho 8 repeated-OD users, 9 supported collapsed-motif users và 0 overlap.

Nhưng comparator motif hiện cho phép sequence chỉ có một location, ví dụ `L0`, tức ngày lặp stationary pattern nhưng không có OD transition.

Vì vậy zero overlap không nên được đọc như hai routine representations khám phá hai nhóm mobility hoàn toàn khác nhau.

Lesson: khi comparator dùng unit khác nhau, eligibility phải match cả support lẫn behavior type. Nếu mục tiêu là mobility routine, collapsed motif comparator nên yêu cầu ít nhất một transition.

## 2026-10-01 — Cửa sổ lịch dài hơn không tự tạo thêm longitudinal support

Stage 06c thử các cửa sổ lịch cố định 28 / 42 / 56 ngày với điều kiện tối thiểu 6 usable days.

Kết quả median usable days trên eligible window chỉ tăng từ 8 → 8 → 9 ngày, trong khi số user có adjacent eligible pair giảm 11 → 9 → 7.

Bài học:

```text
calendar span dài hơn
!=
observation support dày hơn
```

Trong GeoLife, sampling theo thời gian quá không đều. Nếu tăng window chỉ kéo dài khoảng lịch nhưng không thêm nhiều usable observations, detector sẽ mất số cặp so sánh mà không mua được nhiều statistical support.

Vì vậy sau 06c không nên tiếp tục thử 70 / 84-day fixed calendar windows. Hướng đúng hơn là support-indexed windows: gom cố định 6 / 8 / 10 usable days rồi kiểm soát calendar span bằng cap.

## 2026-10-01 — Coarsening giúp representation nhưng không sửa được coverage bottleneck

Exact OD vẫn rất bất ổn ở 06c: median chronological JSD gần 1 và random-partition JSD cũng gần 1. Điều này lặp lại finding của 06b rằng identity-sensitive representation bị sampling chi phối.

Một số coarse feature tốt hơn rõ rệt. Ở 42d:

- cleaned distance / usable day: Spearman ~0.729, chronological > random p95 ở 6.7% pair, bootstrap-width / observed-IQR ~0.814;
- active locations / usable day: Spearman ~0.540, random-p95 exceedance 0%, bootstrap ratio ~0.866.

Tuy nhiên toàn bộ 45 feature × window combinations vẫn fail readiness vì không window nào đạt predeclared 20 adjacent comparable pairs.

Bài học: representation quality và population coverage là hai gate độc lập. Coarsening có thể làm feature ổn định hơn nhưng không tự tạo thêm longitudinal observations.

## 2026-10-01 — Không hạ readiness gate sau khi nhìn kết quả

Ba combination vượt tất cả non-coverage gates:

- 28d time_00_06_share;
- 42d active_location_count_per_usable_day;
- 42d cleaned_distance_km_per_usable_day.

Nhưng comparable pairs tối đa chỉ là 16, thấp hơn gate 20 đã khai báo trước.

Bài học: không nên hạ gate từ 20 xuống 15/16 chỉ vì kết quả hiện tại gần pass. Làm vậy sẽ biến feasibility audit thành post-hoc tuning.

Decision đúng là giữ Stage 07 blocked và thay đổi window construction, không thay đổi acceptance criterion sau khi xem output.

## 2026-10-02 — Support-indexed windows sửa được coverage nhưng không tạo ra change signal đủ mạnh

Stage 06c có thể bị nghi ngờ rằng fixed calendar windows làm mất quá nhiều pair. Stage 06d kiểm tra trực tiếp giả thuyết đó bằng block cố định 6 / 8 / 10 usable days.

Kết quả 6-day và 8-day blocks đạt coverage gate:

- 6d/56: 49 pairs, 18 users;
- 6d/84: 58 pairs, 21 users;
- 8d/56: 26 pairs, 11 users;
- 8d/84: 29 pairs, 11 users.

Vì vậy bottleneck của 06c thực sự đã được sửa.

Nhưng sau khi coverage đủ, không configuration nào có feature pass toàn bộ gate. Điều này quan trọng hơn một failure vì thiếu sample: representation hiện có không cho đủ combination của rank stability, null calibration và bootstrap precision.

Bài học:

```text
fixing coverage
!=
creating longitudinal signal
```

Một feasibility study tốt phải tách hai câu hỏi này ra. 06d cho phép kết luận mạnh hơn rằng broad change detection đang bị giới hạn bởi signal/data quality, không chỉ bởi window construction.

## 2026-10-02 — Cleaned distance là feature gần pass nhất nhưng không được làm tròn threshold

Cleaned distance / usable day có Spearman tốt:

- 6d/56: 0.712;
- 6d/84: 0.697;
- 8d/56: 0.696;
- 8d/84: 0.737.

Nhưng mỗi setting đều miss ít nhất một gate đã khai báo trước:

- 6d/56 bootstrap ratio = 1.030, cao hơn gate 1.0;
- 6d/84 null exceedance = 10.34%, cao hơn 10%;
- 8d/56 = 11.54%;
- 8d/84 = 10.34%.

Các miss rất sát threshold, nhưng chính vì sát nên càng không nên làm tròn hoặc nới gate sau khi xem kết quả.

Bài học: near-pass không phải pass. Predeclared boundary chỉ có ý nghĩa nếu vẫn giữ nguyên khi result nằm ngay bên kia boundary.

## 2026-10-02 — Khi stop rule đã được predeclare, negative result là kết quả cuối chứ không phải lời mời tune tiếp

Final 06d decision table cho cả sáu support/cap configurations:

```text
candidate_features = 0
candidate_primary_features = 0
stage07_ready = False
```

Không chỉ primary feature fail; không feature nào trong full Stage-06c family pass tất cả gates.

Vì vậy đúng theo stop rule, broad within-user Stage 07 phải dừng.

Bài học: một research pipeline cần biết khi nào không nên xây model tiếp. Nếu sau khi sửa representation và coverage mà null-calibrated longitudinal signal vẫn không đủ, tiếp tục thử thêm window sizes sẽ biến audit thành threshold search.

## 2026-10-02 — Work regime nên là profile nhiều trục, không phải một class duy nhất

Stage 07 v1 thử ép evidence từ 03a / 05b / 05c / 06 thành một taxonomy mutually-exclusive.

Kết quả có signal thật: route-centric group có route complexity cao, multi-site group có repeated-route support, fixed-site group có stable secondary anchor và HOME context.

Nhưng overlap làm lộ vấn đề thiết kế:

- 7/7 fixed_site_like vẫn là multi_anchor_state;
- 2/8 route_centric_mobile_like vẫn có stable_single_secondary;
- shifted evidence xuất hiện bên trong multi-site / route-centric thay vì tạo class riêng.

Bài học:

```text
site topology
route topology
schedule timing
mobility complexity
```

là các dimension có thể đồng thời đúng cho một user.

Do đó occupational mobility hợp lý hơn dưới dạng factorized profile, ví dụ:

```text
site: dominant secondary + multiple recurring anchors
route: recurrent / complex
schedule: shifted
mobile complexity: yes
HOME context: supported
```

thay vì ép user vào đúng một nhãn fixed-site hoặc route-centric.

## 2026-10-02 — Coverage của WORK representation vẫn phải được báo cáo như abstention problem

Stage 07 v1 chỉ cho 24/182 user một representation không-abstain:

- 7 single-anchor candidate;
- 9 work-anchor set;
- 8 route/activity-region.

158/182 user còn lại là irregular hoặc insufficient.

Bài học: taxonomy đẹp nhưng chỉ cover một phần nhỏ population thì không được mô tả như universal job/work model. Abstention rate là một result chính, không phải phần phụ.

## 2026-10-02 — Independent evidence yếu không được biến mất sau khi integration

Fixed-site-like có 5/7 user với Stage-05c evidence, nhưng median top-1 independent evidence axes chỉ là 1.0.

Stage 05c trước đó đã kết luận persistence của secondary anchor không đủ để promote thành OFFICE.

Bài học: integration stage không được làm yếu đi negative evidence từ upstream. Stable anchor có thể quyết định representation geometry, nhưng không tự tạo semantic WORK truth.

## 2026-10-02 — Factorization biến overlap từ “classification bug” thành kết quả

Stage 07 v1 coi overlap giữa fixed-site, multi-site và route-centric như vấn đề taxonomy.

Stage 07b giữ các axis riêng và cho thấy overlap rất có cấu trúc:

- 9/9 stable-secondary cũng multiple-recurring;
- 7/9 stable-secondary cũng repeated-route;
- 22/23 repeated-route cũng multiple-recurring;
- 23/23 mobile-complexity cũng multiple-recurring;
- 2/2 shifted-schedule cũng repeated-route.

Bài học: khi các evidence state cùng đúng một cách có hệ thống, không nên cố ép chúng thành mutually-exclusive class. Overlap tự nó là behavioral information.

## 2026-10-02 — Stable secondary không có nghĩa là user chỉ có một work-like place

Representation signature cho thấy:

- 7 user có single-anchor + anchor-set + route-region;
- 2 user có single-anchor + anchor-set;
- không có user nào single-anchor-only.

Bài học: một dominant secondary anchor có thể tồn tại bên trong một hệ nhiều recurring anchors. Vì vậy single-anchor geometry là một candidate view, không phải mô tả đầy đủ toàn bộ mobility structure.

## 2026-10-02 — External semantics nên bắt đầu từ subset có HOME context

07b có 72 multiple-recurring users nhưng chỉ 25 user có HIGH/MEDIUM HOME context.

Nếu enrich POI cho toàn bộ 72 ngay, ta có nguy cơ đưa HOME-like anchors vào semantic WORK audit mà không loại được HOME độc lập.

Bài học: external semantic enrichment nên bắt đầu từ support-qualified subset có HOME context đáng tin, rồi chỉ enrich các recurring non-HOME anchors. Mobility profile vẫn giữ nguyên cho toàn population.

## 2026-10-02 — Source priority phải theo anchor-year distribution, không theo source hấp dẫn nhất

Trước Stage 07c, Gaode 2010 trông hấp dẫn vì có category taxonomy và paper provenance tốt hơn nhiều source khác.

Nhưng measured anchor dates cho thấy:

- 208/225 anchors (92.4%) nằm ở 2008–2009;
- chỉ 1 anchor nằm ở 2010.

Bài học: source selection phải được driven bởi temporal support của target population. Một source rất tốt về metadata nhưng chỉ cover 1 anchor không nên được ưu tiên engineering trước source kém hoàn hảo hơn nhưng cover >90% population.

Với data hiện tại:

- CLCD exact-year có leverage toàn bộ 225 anchors;
- BCL POI 2008 có semantic leverage 208 anchors;
- ohsome có cross-check leverage toàn bộ measured anchors;
- Gaode 2010 hiện là low-priority niche path.

