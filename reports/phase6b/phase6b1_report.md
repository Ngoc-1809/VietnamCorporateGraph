# Phase 6B.1 - Qwen relation discovery vs rule-based candidates (60 bài Phase 5)

Tập: 40 targeted + 20 control từ new144 (seed 20261031, manifest `data/experiments/phase6b/manifest.jsonl`; không dùng dev44/holdout19; KHÔNG phải blind evaluation).
Không có gold: không có Precision/Recall/F1. Auditor 6A chạy ở chế độ deterministic (không gọi Qwen) để không vượt ngân sách và tránh vòng kiểm tra cùng một model.
Số liệu gốc: `benchmark_batch60.json`, `b_only_candidates_batch60.csv` (cột human_label để trống), `llm_rejected_batch60.jsonl`.

## A / B / C (candidate unique theo (subject, predicate, object, status))
| | A rule (toàn bộ 60 bài) | A trong các đoạn Qwen đã đọc | B Qwen | C = A∪B |
|---|---|---|---|---|
| Unique | 41 | 37 | 88 | 117 |
| Bằng chứng khớp văn bản | 41 | 37 | 88 | 117 |
| Qua deterministic (định danh + kiểu + bằng chứng) | 32 | 28 | 75 | 96 |
| Auditor PASS / QUARANTINE | 12 / 20 | 11 / 17 | 6 / 69 | 12 / 84 |
| Loại quan hệ | 8 | 8 | 8 | 9 |

- Trùng (s,p,o, bỏ qua status): 14; cùng bộ ba nhưng khác status: 3; **chỉ B: 73**; **A nằm trong đoạn đã đọc mà B bỏ sót: 23**; A ngoài đoạn Qwen đọc: 4.
- Qwen chỉ đọc tối đa 3 đoạn/bài (148 đoạn); còn 58 đoạn đủ điều kiện chưa đọc do ngân sách 180 lượt -> B không phải phép đo recall đầy đủ.
- Loại quan hệ bổ sung chỉ nhờ B: ACQUIRED (6 candidate). B cũng tìm thêm OWNS_SHARES_IN (30), CHAIR_OF (14), SUBSIDIARY_OF (7), BOARD_MEMBER_OF (7), CEO_OF (4), FOUNDED (3), PARTNERS_WITH (2).
- Duplicate (raw/unique): B 1,24; C 1,31.
- Trạng thái của candidate chỉ B: FACT 57, PLANNED 7, HISTORICAL 5, ENDED 4 (10 candidate có trạng thái bị luật làm chặt hơn Qwen).

## Qwen chỉ B tìm ra: có bằng chứng thật hay suy diễn?
Cả 73 đều có câu bằng chứng khớp văn bản, nhưng **khớp văn bản != quan hệ đúng**. 62/73 qua kiểm tra deterministic nhưng 0/62 được Auditor PASS: 24 chỉ rớt vì "mẫu cấu trúc không tái sinh" (hiển nhiên với candidate chỉ do LLM tìm), còn lại rớt ở định danh chưa grounded (thực thể viết tắt/tên ngắn) hoặc kiểm tra khác. 24/73 không có từ khóa đặc trưng của quan hệ trong câu (dấu hiệu suy diễn).
Đọc tay 30 dòng đầu của CSV (không phải đánh giá):
- Có vẻ đúng, mẫu cũ bỏ sót: danh sách cổ đông ("Công ty có 3 cổ đông: Nguyễn Hữu Tuất (giữ 0,5%)...", Vimo); Elmet Group hoàn tất mua 55,14 triệu cp MSR (ACQUIRED); CTCP Victory Group - công ty con VictoryCons (SUBSIDIARY_OF); "Vũ Văn Tiền - Chủ tịch Hội đồng sáng lập Geleximco"; Hà Thành mua cổ phần Sử Pán 2 từ REE.
- Suy diễn quá mức/đáng nghi: FOUNDED từ "thành lập năm 2024, ... do ông X góp 80%" (góp vốn != người sáng lập), ACQUIRED "Bolt Holdings -> CTCP Chứng khoán" chỉ từ "sau đợt phát hành nắm 62,82%", OWNS từ "cơ quan điều tra xác định ông Bình là cổ đông..." (nội dung điều tra, gán FACT), trạng thái ENDED cho "tỷ lệ sở hữu của bà Ngọc giảm xuống 0,23%" (vẫn còn sở hữu), PLANNED cho MB Capital "đăng ký bán... giảm tỷ lệ" (quan hệ sở hữu hiện tại).
- Lỗi do NER/mention chứ không phải LLM: "Cao Tấn" (tên bị cắt), "CTCP Đầu tư -> Việt Nam", subject chỉ "Bình"/"Ngọc"/"Lực".
- Qwen bị validator loại (109 relation hợp lệ / 109+114 bị loại): ENDPOINT_FAR_FROM_QUOTE 56, TYPE_MISMATCH 23 (ví dụ JOINT_VENTURE_WITH giữa người với người), UNKNOWN_MENTION_ID 14, NEGATED 11, SELF_LOOP 7, EVIDENCE_NOT_VERBATIM 1, DUPLICATE 2. Không có unresolved-endpoint nào; 3 lần gọi trả JSON lỗi.

## Yield (candidate unique / bài)
| | A | B | C |
|---|---|---|---|
| targeted (40) | 0,90 | 2,15 | 2,75 |
| control (20) | 0,25 | 0,15 | 0,40 |
Theo nguồn (C, /bài): Vietstock 3,44; CafeF 1,07; VnEconomy 0,83; Báo Đầu tư 0,38. Đây là candidate, không phải cạnh official; yield tăng chủ yếu ở bài targeted Vietstock (danh sách cổ đông/giao dịch nội bộ) và đi kèm nhiều candidate chưa đạt kiểm tra. Control: B không tốt hơn A.

## Chi phí (batch 60 bài; smoke 6 bài tính riêng: 13 lần gọi, 14.362 prompt token, 1.876 completion token, 19,7 s)
135 lần gọi live (gồm 3 lần lỗi JSON) + 13 cache hit từ smoke; tổng thí nghiệm 148 lần live (<=180). 141.394 prompt token, 27.047 completion token, 256 s thời gian Qwen cho batch (~7 phút tổng, gồm nạp). Auditor deterministic: 0,2 s.

## Kết luận
- Cách này bổ sung cấu trúc câu mà luật bỏ sót (danh sách cổ đông, ACQUIRED, công ty con trong mệnh đề) và nâng số candidate (41 -> 117 unique) nhưng KHÔNG được coi là tăng độ chính xác: chưa có gold; 0 candidate chỉ-B được Auditor PASS; một phần candidate là suy diễn hoặc do lỗi NER.
- Cùng Qwen3.5-9B phát hiện rồi kiểm tra không phải hai phép kiểm chứng độc lập: không dùng sự đồng thuận để báo chất lượng.
- Việc tiếp theo cần người gán nhãn `b_only_candidates_batch60.csv` (human_label) để đo tỷ lệ đúng. Không candidate nào được đưa vào official hay Neo4j.
