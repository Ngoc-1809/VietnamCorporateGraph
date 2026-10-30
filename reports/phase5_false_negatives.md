# Phase 5 - False-negative taxonomy (heuristic triage)

Cue sentences with >=1 in-scope mention. **Cue coverage, not recall.** Categories are rule-based triage, not gold.

| family | cue sentences | with candidate | coverage |
|---|---|---|---|
| ROLE | 476 | 94 | 20% |
| OWN | 330 | 39 | 12% |
| SUBSID | 71 | 8 | 11% |
| ACQUIRE | 91 | 1 | 1% |
| LEND | 87 | 1 | 1% |
| BOND | 65 | 4 | 6% |
| PARTNER | 22 | 3 | 14% |
| SANCTION | 24 | 1 | 4% |
| PROSECUTE | 31 | 5 | 16% |

| missing-candidate category | sentences |
|---|---|
| NO_ENTITY_PAIR | 174 |
| NER_MISSED_ENDPOINT | 27 |
| WRONG_SPAN_OR_TYPE | 139 |
| GENERATOR_MISS | 191 |
| MULTI_ENTITY_SENTENCE | 42 |
| ELIDED_SUBJECT_OR_CROSS_SENTENCE | 234 |
| MODALITY_NOT_FACT | 195 |
| NOT_A_RELATION_GENERIC_CUE | 39 |

### GENERATOR_MISS (examples)
- [ROLE] Nhà máy In tiền Quốc gia có Chủ tịch mới
- [ROLE] Ông Đỗ Giang Nam chính thức được bổ nhiệm làm Chủ tịch HĐTV Nhà máy In tiền Quốc gia.
- [ROLE] Sáng 30/10, Ngân hàng Nhà nước (NHNN) công bố Quyết định số 2368/QĐ-NHNN bổ nhiệm ông Đỗ Giang Nam, Thành viên Hội đồng thành viên (HĐTV), phụ trách HĐTV Nhà máy In tiền Quốc gia, giữ chức Chủ tịch HĐTV.
- [ROLE] Trước đó, ông là Thành viên HĐTV Công ty TNHH MTV Quản lý tài sản của các tổ chức tín dụng Việt Nam (VAMC) và được điều động sang làm Thành viên HĐTV, phụ trách HĐTV Nhà máy In tiền Quốc gia.
- [ROLE] Nhà máy In tiền Quốc gia được thành lập theo Quyết định số 136/CT ngày 22/4/1991 của Chủ tịch Hội đồng Bộ trưởng, kế thừa ngành in tiền hình thành từ năm 1946 với nhà máy in tiền đầu tiên tại đồn điền Chi Nê (Hòa Bình cũ
- [OWN] Năm 2010, Nhà máy chuyển sang mô hình công ty TNHH một thành viên do NHNN nắm 100% vốn, trụ sở tại số 30 Phạm Văn Đồng, Hà Nội.

### MULTI_ENTITY_SENTENCE (examples)
- [ROLE] Ngoài vị trí tại EVS, ông Quân còn giữ vai trò quản trị tại nhiều tổ chức khác như: Thành viên HĐTV Công ty TNHH Ô tô An Dân Vĩnh Phúc, HĐTV Công ty TNHH Đầu tư Thương mại An Dân Hưng Yên, Thành viên HĐQT CTCP G-Automobi
- [ROLE] Doanh nghiệp chi hơn 481 tỷ đồng để sở hữu hơn 24% CTCP Giầy Thượng Đình (UPCoM: GTD); gần 209 tỷ đồng mua 18% vốn CTCP Y tế Aegis từ Chủ tịch Nguyễn Xuân Đông, bà Đỗ Thị Thanh (vợ ông Đông) và ông Nguyễn Xuân Tùng (con 
- [OWN] Doanh nghiệp chi hơn 481 tỷ đồng để sở hữu hơn 24% CTCP Giầy Thượng Đình (UPCoM: GTD); gần 209 tỷ đồng mua 18% vốn CTCP Y tế Aegis từ Chủ tịch Nguyễn Xuân Đông, bà Đỗ Thị Thanh (vợ ông Đông) và ông Nguyễn Xuân Tùng (con 
- [OWN] Vinaconex cũng bán gần 35.4 triệu cổ phiếu Tổng Công ty Đầu tư Nước và Môi trường Việt Nam (UPCoM: VIW) trong giai đoạn 28/05-10/06, qua đó giảm tỷ lệ sở hữu từ 86% xuống còn 25%, đưa VIW từ công ty con thành công ty liê
- [SUBSID] Vinaconex cũng bán gần 35.4 triệu cổ phiếu Tổng Công ty Đầu tư Nước và Môi trường Việt Nam (UPCoM: VIW) trong giai đoạn 28/05-10/06, qua đó giảm tỷ lệ sở hữu từ 86% xuống còn 25%, đưa VIW từ công ty con thành công ty liê
- [ROLE] Hội đồng quản trị Ngân hàng TMCP Kỹ Thương Việt Nam (Techcombank, mã: TCB) vừa công bố Quyết định ngày 28/10/2026 về việc bổ nhiệm bà Phan Thị Hải Yến giữ chức Phó Tổng giám đốc kiêm Giám đốc Khối Ngân hàng Doanh nghiệp 

### ELIDED_SUBJECT_OR_CROSS_SENTENCE (examples)
- [OWN] Về tài sản bảo đảm, doanh nghiệp cho biết tài sản có thể thuộc sở hữu hợp pháp của Vinhomes và/hoặc bên thứ ba theo quy định pháp luật.
- [PROSECUTE] Đây là 3 bị can được xác định là đồng phạm với các đối tượng đã bị Cơ quan An ninh điều tra Công an TP Đà Nẵng khởi tố hồi cuối tháng 7/2026 vừa qua.
- [BOND] Xếp hạng tín nhiệm của ngân hàng phát hành và từng loại trái phiếu giúp nhà đầu tư so sánh rủi ro, trong khi dữ liệu giao dịch trên thị trường hỗ trợ đánh giá liệu mức lợi suất có đủ bù đắp rủi ro hay không.
- [LEND] Đến ngày 24/09, Công ty công bố Nghị quyết HĐQT về việc triển khai khoản vay hợp vốn mới quy mô 150 triệu USD, cũng do SMBC đứng đầu thu xếp, kèm điều khoản cho phép mở rộng quy mô khoản vay.
- [ACQUIRE] Còn lại, DMX chọn repo trái phiếu ( một giao dịch tài chính trong đó một bên bán trái phiếu cho bên kia và đồng thời cam kết sẽ mua lại số trái phiếu đó sau một khoảng thời gian xác định, với một mức giá đã định trước ) 
- [ROLE] - Toyota Việt Nam có Chủ tịch và Tổng giám đốc mới

### NER_MISSED_ENDPOINT (examples)
- [LEND] Theo phương án điều chỉnh được ĐHĐCĐ 2026 thông qua, trong hơn 1,144 tỷ đồng dự kiến thu về, 740 tỷ đồng dùng để trả nợ gốc và lãi vay ngân hàng, 280 tỷ đồng đầu tư vào khu công nghiệp Đất Cuốc, 87.5 tỷ đồng thanh toán c
- [ROLE] Tại công ty, ông đã trải qua các vị trí như: Trưởng phòng Khách hàng định chế (tháng 1/2022-1/2024), Giám đốc chiến lược (tháng 1/2024-7/2026), Phó Tổng Giám đốc (tháng 8-9/2026) và mới nhất làm Quyền Tổng Giám đốc từ th
- [OWN] Tại Tổng công ty Hàng không Việt Nam (Vietnam Airlines), tỷ lệ sở hữu nhà
- [ROLE] Người đại diện theo pháp luật là ông Park Jong Bae, Tổng Giám đốc, đảm nhiệm từ đầu năm 2025; tại lần thay đổi ngày 06/07/2026, công ty đổi một trong ba người đại diện phần vốn.
- [ROLE] Lộ trình lãnh đạo của ông tiếp tục được khẳng định với các vị trí Phó Chủ tịch (từ năm 2016), Trưởng Dự án và Trưởng Ban trong lĩnh vực hoạch định và điều hành bán hàng.
- [ROLE] Cùng với yêu cầu giảm lãi suất cho vay, ông Lê Ngọc Lâm, Chủ tịch Hội đồng quản trị BIDV, kêu gọi các ngân hàng giảm thực chất lãi suất huy động khoảng 0,5% nhằm tạo điều kiện kéo giảm mặt bằng lãi suất cho vay.

### WRONG_SPAN_OR_TYPE (examples)
- [OWN] Tiếp đến, Tập đoàn Công nghiệp Cao su Việt Nam - CTCP (mã: GVR) nắm giữ 4,9 triệu cổ phiếu, chiếm hơn 20% vốn; ước tính nhận về 29,4 tỷ đồng.
- [SUBSID] KSB dồn hơn 515 tỷ đồng hợp tác kinh doanh với công ty con làm KCN Hoa Lư
- [SUBSID] Quý 3/2026 của CTCP Khoáng sản và Xây dựng Bình Dương (HOSE: KSB) lần đầu cho thấy dư hợp tác kinh doanh gần 515.6 tỷ đồng với công ty con Hoa Lư Bình Phước, chủ đầu tư khu công nghiệp Hoa Lư.
- [LEND] Tại ngày 30/09/2026, KSB ghi nhận các số dư với CTCP Đầu tư Hoa Lư Bình Phước gồm 431.3 tỷ đồng trả trước cho người bán, gần 515.6 tỷ đồng hợp tác kinh doanh, hơn 3.5 tỷ đồng cho vay và 46.3 triệu đồng phải thu khác.
- [OWN] với vai trò đại diện chủ sở hữu đối với công ty nông, lâm nghiệp; doanh nghiệp
- [OWN] Ngân hàng Thương mại Cổ phần Quốc tế Việt Nam (VIB, mã: VIB) vừa công bố thông tin về thay đổi sở hữu của cổ đông lớn.