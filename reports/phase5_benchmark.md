# Phase 5 - Benchmark tự sinh từ dữ liệu chạy thật

Không có ground truth: không có Precision/Recall. Số liệu là đếm cạnh theo nhóm bài.

## Nhóm 63 bài gốc: baseline Phase 4 vs Phase 5 (cùng bài)

| chỉ số | dev44 P4 | dev44 P5 | holdout19 P4 | holdout19 P5 |
|---|---|---|---|---|
| articles_processed | 44 | 44 | 19 | 19 |
| official_unique_edges | 4 | 15 | 0 | 5 |
| candidate_unique_edges | 9 | 7 | 5 | 4 |
| graph_entity_nodes | 8 | 25 | 0 | 10 |
| official_relation_types | 3 | 7 | 0 | 4 |
| articles_with_official_edges | 5 | 13 | 0 | 5 |
| official_edges_per_article | 0.0909 | 0.3409 | 0.0 | 0.2632 |
| candidates_per_article | 0.7273 | 0.9091 | 0.3158 | 0.7895 |
| article_grounded_entities | 0 | 95 | 0 | 60 |
| provisional_entities | 409 | 314 | 185 | 128 |
| llm_calls_per_article | 0.4091 | 0.75 | 0.3158 | 0.7368 |

dev44 đã được dùng để sửa mẫu/prompt (không độc lập). holdout19 chỉ được chạy lại, không dùng để chỉnh.

## Bài mới: targeted vs control

| chỉ số | targeted | control |
|---|---|---|
| articles | 108 | 36 |
| mentions | 4295 | 1484 |
| entities_grounded_or_provisional_touched | 993 | 370 |
| candidates_generated | 92 | 8 |
| official_unique_edges | 26 | 0 |
| candidate_unique_edges | 17 | 5 |
| graph_entity_nodes | 46 | 0 |
| official_edges_per_article | 0.241 | 0.0 |
| candidates_per_article | 0.852 | 0.222 |
| articles_with_official | 21 | 0 |
| articles_without_any_edge | 78 | 33 |
| llm_verified_candidates | 74 | 7 |
| llm_valid | 58 | 5 |
| llm_rejected | 16 | 2 |
| duplicate_evidence_merged | 7 | 0 |

Loại quan hệ official - targeted: ['BOARD_MEMBER_OF', 'CEO_OF', 'CHAIR_OF', 'ISSUED_BOND', 'OWNS_SHARES_IN', 'PROSECUTED_BY', 'SUBSIDIARY_OF']; control: []

official theo predicate - targeted: {'CHAIR_OF': 11, 'CEO_OF': 6, 'PROSECUTED_BY': 1, 'SUBSIDIARY_OF': 1, 'OWNS_SHARES_IN': 3, 'BOARD_MEMBER_OF': 3, 'ISSUED_BOND': 1}; control: {}
candidate theo predicate - targeted: {'CEO_OF': 4, 'PARTNERS_WITH': 1, 'CHAIR_OF': 5, 'OWNS_SHARES_IN': 4, 'BOARD_MEMBER_OF': 1, 'PROSECUTED_BY': 1, 'FOUNDED': 1}; control: {'CEO_OF': 3, 'CHAIR_OF': 2}

### Vì sao bài không có cạnh

- targeted: {'candidates_generated_but_all_rejected:ENDPOINT_NOT_VERIFIED': 5, 'cue_sentence_present_but_no_candidate (pattern/NER miss)': 59, 'candidates_generated_but_all_rejected:SUBJECT_UNRESOLVED': 2, 'no_relation_cue_in_article': 7, 'candidates_generated_but_all_rejected:SPAN_BOUNDARY_SUSPECT': 1, 'candidates_generated_but_all_rejected:NEGATED_RELATION': 1, 'candidates_generated_but_all_rejected:OBJECT_UNRESOLVED': 2, 'candidates_generated_but_all_rejected:NON_FACTUAL_RELATION': 1}
- control: {'cue_sentence_present_but_no_candidate (pattern/NER miss)': 21, 'no_relation_cue_in_article': 9, 'candidates_generated_but_all_rejected:NEGATED_RELATION': 1, 'candidates_generated_but_all_rejected:ENDPOINT_NOT_VERIFIED': 1, 'candidates_generated_but_all_rejected:SPAN_BOUNDARY_SUSPECT': 1}

### Lý do loại candidate

- targeted: {'NON_FACTUAL_RELATION': 5, 'ENDPOINT_NOT_VERIFIED': 18, 'NO_EXPLICIT_RELATION': 14, 'LLM_REJECTED': 16, 'NEGATED_RELATION': 2, 'SUBJECT_UNRESOLVED': 8, 'OBJECT_UNRESOLVED': 8, 'VERIFIER_ENTITY_MISMATCH': 8, 'SPAN_ERROR': 2, 'OTHER': 1, 'MISSING_EVIDENCE': 1, 'SPAN_BOUNDARY_SUSPECT': 5, 'COREF_REVIEW': 2}
- control: {'ENDPOINT_NOT_VERIFIED': 2, 'NO_EXPLICIT_RELATION': 2, 'LLM_REJECTED': 2, 'SPAN_BOUNDARY_SUSPECT': 1, 'NEGATED_RELATION': 1}

## Targeted theo chủ đề

| chủ đề | bài | official | candidate | official/bài | loại official |
|---|---|---|---|---|---|
| appointment | 11 | 5 | 6 | 0.455 | ['BOARD_MEMBER_OF', 'CEO_OF', 'CHAIR_OF'] |
| board | 26 | 7 | 4 | 0.269 | ['BOARD_MEMBER_OF', 'CEO_OF', 'CHAIR_OF', 'OWNS_SHARES_IN'] |
| bond | 16 | 1 | 1 | 0.062 | ['ISSUED_BOND'] |
| credit | 9 | 1 | 0 | 0.111 | ['CEO_OF'] |
| jv_partnership | 3 | 0 | 2 | 0.0 | [] |
| mna | 9 | 2 | 1 | 0.222 | ['CHAIR_OF', 'OWNS_SHARES_IN'] |
| prosecution | 8 | 5 | 2 | 0.625 | ['CEO_OF', 'CHAIR_OF', 'PROSECUTED_BY'] |
| sanction | 3 | 0 | 0 | 0.0 | [] |
| shareholding | 17 | 3 | 1 | 0.176 | ['CEO_OF', 'CHAIR_OF'] |
| subsidiary | 6 | 3 | 0 | 0.5 | ['CHAIR_OF', 'SUBSIDIARY_OF'] |

## Targeted theo nguồn

| nguồn | bài | official | candidate | official/bài |
|---|---|---|---|---|
| baodautu | 6 | 0 | 0 | 0.0 |
| cafef | 24 | 3 | 4 | 0.125 |
| vietstock | 68 | 23 | 13 | 0.338 |
| vneconomy | 10 | 0 | 0 | 0.0 |

## Control theo nguồn

| nguồn | bài | official | candidate | official/bài |
|---|---|---|---|---|
| baodautu | 10 | 0 | 3 | 0.0 |
| cafef | 8 | 0 | 0 | 0.0 |
| vietstock | 9 | 0 | 0 | 0.0 |
| vneconomy | 9 | 0 | 2 | 0.0 |