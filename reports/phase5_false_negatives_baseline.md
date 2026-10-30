# Phase 5 - False-negative taxonomy (heuristic triage)

Cue sentences with >=1 in-scope mention. **Cue coverage, not recall.** Categories are rule-based triage, not gold.

| family | cue sentences | with candidate | coverage |
|---|---|---|---|
| ROLE | 106 | 26 | 25% |
| OWN | 84 | 10 | 12% |
| SUBSID | 20 | 1 | 5% |
| ACQUIRE | 20 | 0 | 0% |
| LEND | 57 | 1 | 2% |
| BOND | 11 | 0 | 0% |
| PARTNER | 4 | 0 | 0% |
| SANCTION | 11 | 1 | 9% |
| PROSECUTE | 4 | 1 | 25% |

| missing-candidate category | sentences |
|---|---|
| NO_ENTITY_PAIR | 64 |
| NER_MISSED_ENDPOINT | 9 |
| WRONG_SPAN_OR_TYPE | 34 |
| GENERATOR_MISS | 40 |
| MULTI_ENTITY_SENTENCE | 4 |
| ELIDED_SUBJECT_OR_CROSS_SENTENCE | 61 |
| MODALITY_NOT_FACT | 33 |
| NOT_A_RELATION_GENERIC_CUE | 32 |

### GENERATOR_MISS (examples)
- [ROLE] Ông Đỗ Giang Nam chính thức được bổ nhiệm làm Chủ tịch HĐTV Nhà máy In tiền Quốc gia.
- [ROLE] Trước đó, ông là Thành viên HĐTV Công ty TNHH MTV Quản lý tài sản của các tổ chức tín dụng Việt Nam (VAMC) và được điều động sang làm Thành viên HĐTV, phụ trách HĐTV Nhà máy In tiền Quốc gia.
- [LEND] Điển hình, tháng 4/2026, SACOMBANK giảm 0.5 điểm phần trăm/năm lãi suất ở cả hai chiều huy động và cho vay theo chủ trương của Ngân hàng Nhà nước.
- [LEND] Nửa đầu năm 2026, VPBankS đã huy động thành công tổng cộng 200 triệu USD thông qua các khoản vay hợp vốn do đối tác chiến lược Sumitomo Mitsui Banking Corporation (SMBC) thu xếp, góp phần bổ sung nguồn lực cho hoạt động 
- [OWN] nước tiếp tục nắm giữ 100% vốn tại 9 doanh nghiệp thuộc phạm vi quản lý của Bộ Tài chính cùng với Ngân hàng Agribank.
- [OWN] Hiện tỷ lệ sở hữu nhà nước tại BIDV là 76,73%, còn tại Vietcombank là 74,8%.

### MULTI_ENTITY_SENTENCE (examples)
- [ROLE] Ngoài vị trí tại EVS, ông Quân còn giữ vai trò quản trị tại nhiều tổ chức khác như: Thành viên HĐTV Công ty TNHH Ô tô An Dân Vĩnh Phúc, HĐTV Công ty TNHH Đầu tư Thương mại An Dân Hưng Yên, Thành viên HĐQT CTCP G-Automobi
- [ROLE] Doanh nghiệp chi hơn 481 tỷ đồng để sở hữu hơn 24% CTCP Giầy Thượng Đình (UPCoM: GTD); gần 209 tỷ đồng mua 18% vốn CTCP Y tế Aegis từ Chủ tịch Nguyễn Xuân Đông, bà Đỗ Thị Thanh (vợ ông Đông) và ông Nguyễn Xuân Tùng (con 
- [OWN] Doanh nghiệp chi hơn 481 tỷ đồng để sở hữu hơn 24% CTCP Giầy Thượng Đình (UPCoM: GTD); gần 209 tỷ đồng mua 18% vốn CTCP Y tế Aegis từ Chủ tịch Nguyễn Xuân Đông, bà Đỗ Thị Thanh (vợ ông Đông) và ông Nguyễn Xuân Tùng (con 
- [ROLE] Ngày 29/10, ông Trương Công Thái - Phó Chủ tịch UBND tỉnh Đắk Lắk, cho biết: UBND tỉnh này vừa thành lập tổ công tác liên ngành gồm Sở Nông nghiệp và Môi trường, Sở Tư pháp, Sở Xây dựng, Thanh tra tỉnh, Công an tỉnh và U

### ELIDED_SUBJECT_OR_CROSS_SENTENCE (examples)
- [OWN] Về tài sản bảo đảm, doanh nghiệp cho biết tài sản có thể thuộc sở hữu hợp pháp của Vinhomes và/hoặc bên thứ ba theo quy định pháp luật.
- [ROLE] Nhà máy In tiền Quốc gia được thành lập theo Quyết định số 136/CT ngày 22/4/1991 của Chủ tịch Hội đồng Bộ trưởng, kế thừa ngành in tiền hình thành từ năm 1946 với nhà máy in tiền đầu tiên tại đồn điền Chi Nê (Hòa Bình cũ
- [OWN] Năm 2010, Nhà máy chuyển sang mô hình công ty TNHH một thành viên do NHNN nắm 100% vốn, trụ sở tại số 30 Phạm Văn Đồng, Hà Nội.
- [ROLE] Ông Nguyễn Anh Phú Nguyên từ nhiệm chức Thành viên HĐQT Nam Tân Uyên với lý do cá nhân.
- [PROSECUTE] Đây là 3 bị can được xác định là đồng phạm với các đối tượng đã bị Cơ quan An ninh điều tra Công an TP Đà Nẵng khởi tố hồi cuối tháng 7/2026 vừa qua.
- [BOND] Xếp hạng tín nhiệm của ngân hàng phát hành và từng loại trái phiếu giúp nhà đầu tư so sánh rủi ro, trong khi dữ liệu giao dịch trên thị trường hỗ trợ đánh giá liệu mức lợi suất có đủ bù đắp rủi ro hay không.

### NER_MISSED_ENDPOINT (examples)
- [LEND] Theo phương án điều chỉnh được ĐHĐCĐ 2026 thông qua, trong hơn 1,144 tỷ đồng dự kiến thu về, 740 tỷ đồng dùng để trả nợ gốc và lãi vay ngân hàng, 280 tỷ đồng đầu tư vào khu công nghiệp Đất Cuốc, 87.5 tỷ đồng thanh toán c
- [ROLE] Tại công ty, ông đã trải qua các vị trí như: Trưởng phòng Khách hàng định chế (tháng 1/2022-1/2024), Giám đốc chiến lược (tháng 1/2024-7/2026), Phó Tổng Giám đốc (tháng 8-9/2026) và mới nhất làm Quyền Tổng Giám đốc từ th
- [OWN] Tại Tổng công ty Hàng không Việt Nam (Vietnam Airlines), tỷ lệ sở hữu nhà
- [ROLE] Người đại diện theo pháp luật là ông Park Jong Bae, Tổng Giám đốc, đảm nhiệm từ đầu năm 2025; tại lần thay đổi ngày 06/07/2026, công ty đổi một trong ba người đại diện phần vốn.
- [ROLE] Chủ tịch VBOX Tô Thị Phương Thảo: Gần 30 năm theo đuổi mỹ thuật ứng dụng và hành trình hơn một thập kỷ đồng hành cùng BIDV
- [ROLE] Lộ trình lãnh đạo của ông tiếp tục được khẳng định với các vị trí Phó Chủ tịch (từ năm 2016), Trưởng Dự án và Trưởng Ban trong lĩnh vực hoạch định và điều hành bán hàng.

### WRONG_SPAN_OR_TYPE (examples)
- [OWN] Tiếp đến, Tập đoàn Công nghiệp Cao su Việt Nam - CTCP (mã: GVR) nắm giữ 4,9 triệu cổ phiếu, chiếm hơn 20% vốn; ước tính nhận về 29,4 tỷ đồng.
- [OWN] CTCP Đầu tư Sài Gòn VRG (mã: SIP) nắm 4,78 triệu cổ phiếu, chiếm gần 20% vốn điều lệ; ước tính nhận về 28,7 tỷ đồng.
- [SUBSID] KSB dồn hơn 515 tỷ đồng hợp tác kinh doanh với công ty con làm KCN Hoa Lư
- [SUBSID] Quý 3/2026 của CTCP Khoáng sản và Xây dựng Bình Dương (HOSE: KSB) lần đầu cho thấy dư hợp tác kinh doanh gần 515.6 tỷ đồng với công ty con Hoa Lư Bình Phước, chủ đầu tư khu công nghiệp Hoa Lư.
- [LEND] Tại ngày 30/09/2026, KSB ghi nhận các số dư với CTCP Đầu tư Hoa Lư Bình Phước gồm 431.3 tỷ đồng trả trước cho người bán, gần 515.6 tỷ đồng hợp tác kinh doanh, hơn 3.5 tỷ đồng cho vay và 46.3 triệu đồng phải thu khác.
- [OWN] Hoa Lư Bình Phước là công ty con KSB sở hữu gián tiếp 93.24% vốn.