# Phase 6B.2 - Hybrid relation validation (60 bài, dùng lại kết quả 6B.1; không crawl, không gọi Qwen)

Không có gold: Precision/Recall/F1 = NOT EVALUATED. Không tuyên bố Precision >= 90%. Neo4j, official edges, registry không đổi.
Code: `src/vckg/validation/hybrid_validator.py` (validator mới, version `hybrid-validator-v1`), `hybrid_qa.py` (runner). Auditor 6A (`auto_auditor.py`) giữ nguyên và vẫn chạy làm baseline.
Outputs: `data/experiments/phase6b/hybrid_qa/` (results/staging_validated/quarantine/rejected jsonl), `reports/phase6b/hybrid_qa/` (summary.json, all_candidates_hybrid_qa.csv, review_sample_40.csv).

## 1. Đối soát số liệu
41 + 88 − 12 = 117 (khớp). B (88 khóa) = 12 trùng khóa với A + 3 cùng bộ ba khác status + **73 chỉ-B**. 73 là số khóa (subject, predicate, object, **status**); tính theo bộ ba riêng biệt là 67 (5 bộ ba xuất hiện với >=2 status). Không có sai số học. Lỗi nằm ở báo cáo 6B.1: `both_same_status = 0` do so sánh `["LLM","RULE"]` với `["BOTH"]`; giá trị đúng là 12. Đã sửa code báo cáo, bản cũ giữ ở `benchmark_batch60.v1_with_reporting_bug.json`. A: 44 candidate thô -> 41 khóa; B: 109 relation thô -> 88 khóa.
Job `p6b1-batch60` vẫn ghi FAILED/exit 1 (không sửa); ghi chú khôi phục ở `logs/jobs/p6b1-batch60.note.md`.

## 2. Hai tầng QA
- Hard validation: evidence khớp bài, mention nằm trong evidence, kiểu thực thể, self-loop, phủ định (từ "không/chưa" đơn lẻ chỉ QUARANTINE, không REJECT), trạng thái thời gian, danh tính bảo thủ (tên người 1 từ, tên tổ chức chung/bị cắt, id người thuộc bài khác, PROVISIONAL).
- Điều kiện ngữ nghĩa theo predicate viết trên câu (không gọi lại generator): sở hữu vs chỉ đăng ký mua/bán (mua đã hoàn tất tính là có), giảm tỷ lệ nhưng còn dương != ENDED, ACQUIRED cần hành vi mua và đúng bên mua (không suy từ % sau phát hành), FOUNDED != góp vốn/người đứng tên thuê, chức vụ không gán cho thân nhân, chức vụ quá khứ/đơn xin từ nhiệm, công ty mẹ/con theo ngữ pháp (không phải cùng tập đoàn/hợp tác), bên bị phạt != bên nhận hồ sơ, khởi tố/truy tố, trái phiếu có đủ số liệu trong bài.
- Rule agreement chỉ là tín hiệu: RULE_SUPPORTED / SEMANTIC_ONLY / CONTRADICTED / INSUFFICIENT_EVIDENCE. PASS/AUTO_CORRECT cần RULE_SUPPORTED. **SEMANTIC_ONLY không bao giờ thành PASS**; nếu mọi kiểm tra khác đạt thì QUARANTINE loại `SEMANTIC_ONLY_CLEAN` (ưu tiên duyệt). Qwen không dùng ở đây: cùng model phát hiện rồi kiểm tra không phải kiểm chứng độc lập.

## 3. A/B/C, trước (6A) và sau (hybrid)
| | A (41) | B (88) | C (117) | chỉ-B (73) |
|---|---|---|---|---|
| 6A: PASS/QUARANTINE/REJECT/chưa audit* | 12/20/2/7 | 6/69/0/13 | 12/84/2/19 | 0/62/0/11 |
| hybrid: PASS/QUARANTINE/REJECT | 10/30/1 | 6/81/1 | 10/105/2 | 0/72/1 |
| hybrid: AUTO_CORRECT | 0 | 0 | 0 | 0 |
| bị 6A chặn CHỈ vì luật không tái tạo | 0 | 24 | 24 | 24 |
| hybrid: SEMANTIC_ONLY_CLEAN (không bị chặn bởi luật, nhưng không tự PASS) | 0 | 12 | 12 | 12 |
| hybrid: INSUFFICIENT_EVIDENCE | 0 | 23 | 23 | 23 |
| qua kiểm tra bằng chứng + kiểu thực thể | 38 | 88 | 114 | 73 |
| nghi suy diễn (thiếu bằng chứng ngữ nghĩa hoặc không có từ khóa) | 5 | 35 | 40 | 35 |
| loại quan hệ trong staging (PASS) | 4 | 3 | 4 | 0 |
*"chưa audit" = chưa qua kiểm tra sơ bộ endpoint (6A chỉ audit candidate có đủ id).
Staging validated: 10 cạnh, 17 entity, 4 loại (CHAIR_OF 5, OWNS_SHARES_IN 2, CEO_OF 2, BOARD_MEMBER_OF 1). 6A baseline trên cùng tập cho 12 PASS; hybrid nghiêm hơn ở danh tính/ngữ nghĩa nên ít hơn 2. Targeted: 109 candidate -> 10 PASS/97 QUARANTINE/2 REJECT; control: 8 -> 8 QUARANTINE.

## 4. Candidate mới vượt lỗi vòng tròn
Trong 24 candidate từng bị chặn chỉ vì luật không tái tạo: 12 là SEMANTIC_ONLY_CLEAN (vượt kiểm tra bằng chứng, kiểu, trạng thái, ngữ nghĩa theo predicate; vẫn chờ người duyệt), 8-9 bị INSUFFICIENT (cue thiếu, FOUNDED chỉ góp vốn, hướng mẹ/con chưa chứng minh), phần còn lại bị danh tính. Ví dụ SEMANTIC_ONLY_CLEAN: Elmet Group hoàn tất mua cổ phần MSR; ABBank-ABS ký thỏa thuận hợp tác; Vũ Văn Tiền - Chủ tịch Hội đồng sáng lập (xem dưới); danh sách cổ đông Merufa nắm %; Đào Trung Kiên sở hữu 418.466 cp PNJ.

## 5. Vẫn bị chặn và vì sao
Nguyên nhân chính **không phải luật mà là danh tính**: 53/117 candidate chỉ bị chặn vì `IDENTITY_NOT_GROUNDED` (thực thể PROVISIONAL) dù ngữ nghĩa đạt (32 trong số đó là LLM-only). Còn lại: tên người 1 từ (6), span bị cắt (3), đơn xin từ nhiệm (2), chức vụ trong câu vụ án (2), bằng chứng là chú thích/câu ngắn (2), tên tổ chức chung (1), phủ định mơ hồ (1).

## 6. Suy diễn / nhầm trạng thái phát hiện được
- Đã bắt: FOUNDED từ "do ông X góp 80%" (3 candidate) và từ "thuê... thành lập... vỏ bọc"; ACQUIRED "Bolt Holdings" chỉ từ % sau phát hành và "đăng ký mua" (chuyển PLANNED, không official); Masan bị gán là bên mua thay vì Lepus (ACQUIRER_NOT_AGENT); Cao Thị Ngọc Sương CHAIR_OF Novaland (chức vụ của con trai: FAMILY_MEMBER_ATTRIBUTION, REJECT); OWNS_SHARES_IN của "MB Capital đăng ký bán" (chỉ đăng ký); "Công ty ... thoái vốn cho Hà Thành" mua vs bán; sửa ENDED -> FACT khi tỷ lệ vẫn dương (Ngọc/SBT, Ariston/Mutosi); "bán ký quỹ ... không gửi cho HNX" không còn bị coi là cơ quan xử phạt.
- Sửa trong quá trình làm: lần chạy đầu gán nhầm ENDED->FACT cho "cổ đông lớn thoái vốn" và REJECT trên từ "không" chung; đã siết lại (có regression test).
- Giới hạn: "Chủ tịch Hội đồng sáng lập" vẫn nằm trong SEMANTIC_ONLY_CLEAN ở một ca vì cue "chủ tịch" khớp; cần người duyệt. Danh sách HĐQT ("HĐQT mới gồm ...") bị INSUFFICIENT dù đúng (cue thành viên danh sách chưa được mã hóa).

## 7. Review set
`reports/phase6b/hybrid_qa/review_sample_40.csv` (40 dòng, seed 20261101; gold/human_label để trống): 9 LLM-only SEMANTIC_ONLY_CLEAN, 8 LLM-only bị chặn cứng, 8 rule-only, 6 cả hai, 9 negative/ambiguous. Không cần duyệt hết 117; NOT EVALUATED cho tới khi có nhãn.

## 8. Hạn chế
Chưa có gold nên không biết tỷ lệ cạnh đúng bị chặn nhầm hay sai lọt qua; luật từ khóa tiếng Việt có thể bỏ sót; Qwen chưa tham gia nên chưa đo lỗi của riêng semantic-assessment; PASS vẫn phụ thuộc registry/danh tính (53 ca bị chặn chỉ vì danh tính). Chưa có candidate nào vào Neo4j hay official.
