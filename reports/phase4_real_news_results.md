# Phase 4 - Kết quả thí nghiệm có kiểm soát trên bài báo thật (30/10/2026)

Không phải production crawl. Mọi số liệu dưới đây do pipeline thật tạo ra (GLiNER2.5 CUDA fp16 + Entity Resolver + Qwen3.5-9B qua Ollama);
test double (FakeNER/AcceptAll) chỉ có trong unit test. **Chưa có ground truth nên Precision/Recall/F1 = NOT EVALUATED**;
mọi nhận xét "đúng/sai" bên dưới là đọc tay của người viết báo cáo, không phải đánh giá.

## 1. Dữ liệu

| Tập | Số bài | Nguồn | Vai trò |
|---|---|---|---|
| dev | 44 | CafeF 15, VnEconomy 15, Vietstock 12, Báo Đầu tư 2 | dùng để chẩn đoán lỗi và bổ sung mẫu quan hệ |
| hold-out | 19 | CafeF 14, VnEconomy 4, Vietstock 1 | crawl SAU khi đóng băng phần trích xuất; không có mẫu/ngưỡng nào được sửa theo lỗi của tập này |
| 9 bài Phase 3 | 9 | CafeF, Vietstock, VnEconomy | so sánh trước/sau |

- Tổng 63 bài (hơi vượt mức 30-60 vì hold-out là phần còn lại của pool hiện có), danh sách URL + điểm tín hiệu: `data/outputs/experiment/selected_articles.jsonl`, `selected_holdout.jsonl`.
- Chọn bài bằng điểm từ khóa quan hệ (bổ nhiệm, HĐQT, cổ đông lớn, mua lại, công ty con, cấp tín dụng, trái phiếu, xử phạt, khởi tố, hợp tác...) trên tiêu đề/tóm tắt/slug: đây là **thiên lệch có chủ ý** về bài có tín hiệu quan hệ, không phải mẫu đại diện của báo chí.
- Crawler: robots.txt, delay 2s/host, retry+backoff, chỉ trang công khai (RSS; riêng Báo Đầu tư dùng các trang chuyên mục công khai có trong sitemap.xml của chính site vì RSS trả 0 bài, `sitemap-news.xml` trả HTML và sitemap theo tháng trả "Not found"). Không đăng nhập/không vượt paywall.
- Báo Đầu tư: adapter hoạt động (69 URL khám phá, 2 bài vượt ngưỡng tín hiệu được lấy và trích xuất); mẫu quá nhỏ để kết luận gì về nguồn này.

## 2. Funnel (tập dev 44 bài, mã cuối cùng)

| Bước | Dev (44) | Hold-out (19) |
|---|---|---|
| Mentions (GLiNER cấp câu + từ điển registry) | 1.580 | 534 |
| Trong scope (không phải chỉ số/sàn/chức danh/từ chung) | 1.326 | 487 |
| Linked VERIFIED (định danh từ nguồn phụ) | 187 (14,1% trong scope) | 35 (7,2%) |
| Linked PROVISIONAL (thực thể mới từ bài báo) | 974 (73,5%) | 410 (84,2%) |
| Ambiguous / Unresolved | 7 / 158 | 0 / 42 |
| Cặp mention cùng câu hợp kiểu | 912 | 323 |
| Candidate có mẫu quan hệ gắn với cả 2 endpoint | 32 | 6 |
| Lọc trước LLM (endpoint unresolved, trùng...) | 14 | 0 |
| Gọi Qwen (lần chạy cuối, một phần lấy từ cache) | 18 (2 live + 16 cache) | 6 (cache) |
| Qwen valid=true / false | 15 / 3 | 6 / 0 |
| Validator: official / candidate-edge / rejected (outcome) | 5 / 10 / 17 | 0 / 6 / 0 |
| **Cạnh logic** (sau gộp bằng chứng) official / candidate-only | **4 / 9** | **0 / 5** |

Lý do loại (đếm theo mã, một candidate có thể có nhiều mã): dev: ENDPOINT_NOT_VERIFIED 11, OBJECT_UNRESOLVED 12, SUBJECT_UNRESOLVED 2, NO_EXPLICIT_RELATION 3, LLM_REJECTED 3. Hold-out: ENDPOINT_NOT_VERIFIED 6.

**Cách đọc con số linking:** "73,5% provisional" KHÔNG phải độ chính xác linking. Đó là các thực thể được tạo mới từ bài báo, chưa có định danh bên ngoài.
Chỉ 14,1% (dev) và 7,2% (hold-out) mention trong scope khớp với định danh VERIFIED. Trên 9 bài Phase 3: baseline 23/158 (14,6% trong scope, chỉ từ từ điển seed viết tay) -> 17 VERIFIED (4,9%) + 275 PROVISIONAL (79,7%) với registry provider; 0 VERIFIED + 304 PROVISIONAL (88,9%) với registry seed. Số mention tăng từ 173 lên ~395 một phần vì GLiNER chạy cấp câu (xem §6).

## 3. Registry growth

| | Trước | Sau |
|---|---|---|
| Registry provider (Vietstock sitemap, `identity_only=1`, VERIFIED) | 2.267 | 2.267 |
| + PROVISIONAL tạo từ 44 bài dev | | +409 -> 2.676 |
| + PROVISIONAL tạo từ 19 bài hold-out (registry riêng) | | +185 -> 2.452 |
| Gộp cluster người (cùng tên chuẩn hóa + cùng tổ chức, có log) | | dev 4, hold-out 1 |

**Đây là hàng registry, KHÔNG phải node đồ thị.** Số thực thể thực sự nằm trong cạnh có bằng chứng báo chí: **23 (dev) và 10 (hold-out)**. So với mục tiêu 2.000 entity / 5.000 quan hệ ngày 11/11/2026: còn rất xa; không được dùng 2.267 dòng registry để báo cáo KPI.

## 4. Chi phí LLM và thời gian

| Lần chạy | Gọi live | Cache hit | Thời gian LLM | Prompt / completion token |
|---|---|---|---|---|
| dev, prompt v3 (run1) | 12 | 0 | 15,0 s (TB 1.251 ms/lần) | 5.673 / 1.582 |
| dev, prompt v4 NER cấp câu (run2) | 17 | 0 | 22,7 s (TB 1.332 ms) | 9.567 / 2.363 |
| dev, NER cả bài | 6 | 12 | 7,4 s | 3.321 / 770 |
| dev, lần chạy cuối | 2 | 16 | 2,2 s | 1.092 / 226 |
| hold-out, lần chạy cuối | 0 | 6 | 0 | 0 |

- Tiết kiệm: lọc trước LLM bỏ 14 lần gọi ở dev (endpoint unresolved, trùng); cache SQLite (khóa = model + prompt_version + câu + 2 mention + predicate + cue) giúp các lần chạy lại gần như 0 lần gọi. Lọc câu phủ định chắc chắn (luật) nằm trong cùng bước, có test.
- So với Phase 3: 14 candidate trên 9 bài (14 lần gọi) -> 8 candidate cho cùng 9 bài (8 lần gọi lúc chạy nguội). Giảm số lần gọi nhưng chưa có benchmark recall, nên **không** khẳng định không mất recall.
- Thời gian xử lý trung bình trong tiến trình: 0,42-0,94 s/bài (gồm NER + LLM nếu có; không gồm ~10-60 s nạp model GLiNER một lần). Wall time 37,9 s/44 bài và 24,2 s/19 bài ở lần chạy cuối.
- GPU: GLiNER fp16 ~1,2 GB VRAM; Qwen qua Ollama; chạy tuần tự trong cùng máy, trong giới hạn 16 GB.

## 5. Ví dụ quan hệ thật (đọc tay; 4 official + các candidate)

Định nghĩa: **official** = Qwen valid + trạng thái FACT/HISTORICAL/ENDED + không có lý do chặn + endpoint đạt chính sách (tổ chức: VERIFIED; người: cụm định danh trong bài có đủ họ tên; cơ quan: VERIFIED/PROVISIONAL).
**candidate-edge** = có bằng chứng và verdict hợp lệ nhưng endpoint tổ chức mới là PROVISIONAL (`ENDPOINT_NOT_VERIFIED`) hoặc trạng thái không phải sự thật đã xảy ra; chờ người duyệt, không tính vào đồ thị chính thức.

| # | Subject -[Predicate]-> Object | Trạng thái | Quyết định validator | Nguồn / câu bằng chứng |
|---|---|---|---|---|
| 1 | CTCP Cao su Phước Hòa -[OWNS_SHARES_IN]-> NTC | FACT | **official** (2 tổ chức VERIFIED qua mã PHR, NTC) | https://cafef.vn/mot-thanh-vien-hdqt-nam-tan-uyen-tu-nhiem-188261029152517523.chn : "CTCP Cao su Phước Hòa (mã: PHR) là cổ đông lớn nhất của NTC sở hữu 7,88 triệu cổ phiếu, tương ứng 32,85% vốn điều lệ" |
| 2 | CTCP Nhiệt điện Phả Lại -[SANCTIONED_BY]-> Cục Thuế TP. Hải Phòng | FACT | **official** (hướng công ty->cơ quan, từ mẫu "nhận được quyết định xử phạt ... từ") | http://vietstock.vn/2026/10/ppc-bi-phat-va-truy-thu-thue-hon-800-trieu-737-1508493.htm : "CTCP Nhiệt điện Phả Lại (HOSE: PPC) thông báo nhận được quyết định xử phạt vi phạm hành chính về thuế từ Cục Thuế TP. Hải Phòng" |
| 3 | Chu Đức Anh -[PROSECUTED_BY]-> Cơ quan An ninh điều tra Công an TP Đà Nẵng | FACT (bị khởi tố; **không** hàm ý bị kết tội) | **official** | https://cafef.vn/ra-quyet-dinh-khoi-to-vu-thi-thanh-sn-1978-trong-chuyen-an-lon-lien-quan-so-tien-700-ty-dong-188261029215256655.chn : "... Cơ quan An ninh điều tra Công an TP Đà Nẵng đã khởi tố ba bị can gồm Chu Đức Anh ..." (chỉ người đầu danh sách được trích) |
| 4 | Nguyễn Thùy Nga -[OWNS_SHARES_IN]-> VIB | FACT | **official**; 2 bằng chứng từ 2 bài (CafeF "bà Nga" được gán cho cụm "Nguyễn Thùy Nga" cùng bài, rồi gộp với cụm của Vietstock vì cùng họ tên + cùng tổ chức VIB, có log merge) | http://vietstock.vn/2026/10/hai-doanh-nghiep-cung-nhom-lien-quan-so-huu-hon-86-von-vib-757-1508404.htm : "bà Nguyễn Thùy Nga đang sở hữu 3.386% vốn tại VIB" |
| 5 | Tô Thị Phương Thảo -[CHAIR_OF]-> CTCP Bao bì Cao cấp Việt Nam | FACT | candidate-edge (ENDPOINT_NOT_VERIFIED: công ty chưa niêm yết, không có trong nguồn định danh) | https://cafef.vn/chu-tich-vbox-to-thi-phuong-thao-gan-30-nam-theo-duoi-my-thuat-ung-dung-va-hanh-trinh-hon-mot-thap-ky-dong-hanh-cung-bidv-188261029132837634.chn : "chị Tô Thị Phương Thảo, Chủ tịch HĐQT CTCP Bao bì Cao cấp Việt Nam (VBOX)" |
| 6 | Đoàn Văn Hiểu Em -[CEO_OF]-> Điện Máy Xanh | FACT | candidate-edge | https://cafef.vn/dien-may-xanh-du-kien-doanh-thu-hon-8-ty-usd-vao-nam-2030-loi-nhuan-tang-gap-3-lan-sau-5-nam-188261029152418607.chn : "Tổng giám đốc Điện Máy Xanh – ông Đoàn Văn Hiểu Em cho biết..." |
| 7 | Vũ Đăng Linh -[BOARD_MEMBER_OF]-> Điện Máy Xanh | FACT | candidate-edge | https://cafef.vn/lanh-dao-dien-may-xanh-noi-gi-ve-khoan-dau-tu-vao-trai-phieu-bat-dong-san-188261030072328743.chn : "ông Vũ Đăng Linh, Thành viên HĐQT Điện Máy Xanh cho biết..." |
| 8 | Nguyễn Quốc Cường -[CHAIR_OF]-> Công ty Cổ phần Chánh Nghĩa Quốc Cường (hold-out) | FACT | candidate-edge | https://cafef.vn/cuong-do-la-quyet-tang-lamborghini-30-ty-mau-vang-ruc-ro-cho-khach-mua-nha-188261030110316711.chn : "Doanh nhân Nguyễn Quốc Cường (Cường Đô-la), Chủ tịch HĐQT Công ty Cổ phần Chánh Nghĩa Quốc Cường (C-Holdings)" |
| 9 | Hà Đức Hiếu -[BOARD_MEMBER_OF]-> Bluemarq Group (hold-out; 2 bằng chứng cùng bài, tên có/không CTCP gộp đúng 1 cạnh) | FACT | candidate-edge | https://cafef.vn/mot-thanh-vien-hdqt-dxg-muon-gom-15-trieu-co-phieu-188261030085906133.chn : "Ông Hà Đức Hiếu- Thành viên HĐQT của CTCP Bluemarq Group (MCK: DXG, sàn HoSE)..." |
| 10 | Tổng Công ty Phát điện 2 - CTCP -[OWNS_SHARES_IN]-> PPC | FACT | candidate-edge (cổ đông là PROVISIONAL; "- CTCP" đã được nối vào tên) | cùng bài #2 : "Tổng Công ty Phát điện 2 - CTCP (EVNGENCO 2) là cổ đông lớn nhất của PPC, sở hữu gần 50 triệu cp, tương ứng 30% vốn điều lệ" |

Loại quan hệ đã xuất hiện trong kết quả cuối: CHAIR_OF, CEO_OF, BOARD_MEMBER_OF, FOUNDED, OWNS_SHARES_IN (official + candidate), SANCTIONED_BY, PROSECUTED_BY (official). Chưa thấy: SUBSIDIARY_OF, ACQUIRED, LENDS_TO, JOINT_VENTURE_WITH, PARTNERS_WITH, ISSUED_BOND (chưa có mẫu cho BondIssue). Mẫu có test đơn vị cho SUBSIDIARY_OF, ACQUIRED, LENDS_TO, nhưng **chưa được xác nhận trên bài thật**.

Đọc tay toàn bộ 4 cạnh official và 14 cạnh candidate: không thấy cạnh sai rõ ràng; có sắc thái cần người duyệt:
(a) FOUNDED "Nguyễn Trung Hiếu -> Công ty TNHH Thương mại XNK Tư Gia": câu nói ông được thuê thành lập công ty làm "vỏ bọc" (người đứng tên, không phải sáng lập viên đúng nghĩa thương mại);
(b) CHAIR_OF "Christine Lagarde -> ECB": đúng nhưng thực thể nước ngoài, ngoài phạm vi doanh nghiệp Việt Nam;
(c) "Phó Chủ tịch Vinacas -> BOARD_MEMBER_OF": Vinacas là hiệp hội, ánh xạ "Phó Chủ tịch" thành thành viên HĐQT là mở rộng của mẫu; (d) nhãn BANK của GLiNER cho "Công ty cổ phần Sáng Ban Mai" là nhầm phân loại con.

## 6. Quan sát phương pháp (không phải kết luận chất lượng)

1. **Qwen từ chối nhầm** (prompt v3): "Phó Chủ tịch HĐQT G-Group" và "từ nhiệm chức Thành viên HĐQT ..." bị trả `valid=false / NO_RELATION` do prompt không nói rõ quan hệ đã chấm dứt/đã dự kiến vẫn là `valid=true`. Prompt v4 làm rõ điểm này (đây là sửa ngữ nghĩa, không phải chỉnh ngưỡng). Chưa đo lại tỷ lệ từ chối nhầm trên tập gán nhãn.
2. **Qwen gán HISTORICAL cho câu hiện tại** (ví dụ "Chủ tịch ... Viettel" trong bài về sự kiện đã qua). Validator chỉ chấp nhận HISTORICAL/ENDED của LLM khi tầng luật cũng thấy dấu hiệu từ vựng (`llm_status=HISTORICAL_ignored_no_cue` được ghi vào validation_status). PLANNED/ALLEGED/DENIED của LLM luôn có hiệu lực (chỉ làm chặt thêm).
3. **Điểm tin cậy**: Qwen không trả xác suất; trường `confidence` đã bị bỏ khỏi hợp đồng JSON. `relation_score=null`, `score_available=false` cho mọi cạnh. `ner_score` là điểm GLiNER thật (null cho mention từ từ điển). `linking_score` chỉ có ở khớp mờ (rapidfuzz). Chưa hiệu chuẩn gì.
4. **NER cấp câu vs cả bài** (cùng 44 bài, cùng mã): cấp câu 1.580 mention / 29 candidate (lần so sánh) / 13 cạnh; cả bài 853 mention / 21 candidate / 14 cạnh. Mỗi chế độ tìm được cạnh mà chế độ kia bỏ sót (cấp câu: 2 cạnh đúng thêm, mất 3). **Không chế độ nào được chứng minh tốt hơn**; cấp câu được đặt mặc định vì nút thắt là recall quan hệ, đổi lại +85% mention (nhiều thực thể PROVISIONAL rác). `--doc-ner` để so sánh.
5. **Giới hạn NER còn lại**: GLiNER đôi khi chia nhỏ tên ("Nhà máy" + "tiền Quốc gia" trong "Chủ tịch HĐTV Nhà máy In tiền Quốc gia") hoặc gán loại sai (BANK cho công ty); tầng luật chỉ sửa được các lỗi hệ thống đã biết (tiền tố chức danh/HĐQT/HĐTV, hậu tố "- CTCP", "Việt Nam").
6. **Recall mẫu quan hệ (chỉ số gián tiếp, không phải recall)**: ở dev vẫn có câu chứa từ khóa tín hiệu và >=2 mention nhưng không sinh candidate: ROLE 36/49, OWN 23/30, SUBSID 9/9, PARTNER 7/7, LEND 15/16 (đo trước vòng bổ sung cuối). Phần lớn là câu không nêu quan hệ giữa hai thực thể (ví dụ "lãi suất cho vay"), một phần là cấu trúc chưa có mẫu (danh sách nhiều người, chủ ngữ ẩn, "hợp tác kinh doanh với công ty con").
7. Bài của tập dev đã được dùng để bổ sung mẫu (parenthetical, đơn vị "cp", "nhận được quyết định xử phạt ... từ", "bị can", "kiêm" đảo thứ tự, "công ty con 100% vốn của", HĐTV). Vì vậy **kết quả dev không còn là phép đo độc lập**. Hold-out chỉ có 19 bài / 6 candidate / 0 official - quá nhỏ để rút kết luận.

## 7. Trạng thái so với mục tiêu

Hiện đạt: pipeline chạy end-to-end với mô hình thật và có truy vết bằng chứng. Chưa đạt: 4 cạnh official + 14 candidate trên 63 bài; không có số liệu precision.
Nút thắt hiện tại là (1) định danh tổ chức chưa niêm yết (đa số công ty trong bài không có trong nguồn định danh nên chỉ ra được candidate), (2) độ phủ mẫu quan hệ và NER trên báo tiếng Việt.

## 8. File kết quả

`data/outputs/experiment/final_dev/`, `final_holdout/` (entities, candidates, verdicts, relations, relations_official, relations_candidate, candidate_outcomes.csv, summary.json);
`data/outputs/phase4_9art_seedonly/`, `phase4_9art_full/` (9 bài Phase 3, hai kiểu registry); `data/outputs/baseline_phase3/` (Phase 3 gốc, không sửa);
`reports/phase4_annotation_sample.csv` (120 câu thật, cột gold để trống).

