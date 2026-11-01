# Campaign summary final (2026-11-01T15:40:23+07:00)

No gold labels exist: PASS/QUARANTINE counts are rule outcomes, NOT precision/recall/F1.

- articles: discovered 32929, downloaded 8, parsed 8, processed 8, deferred 0, failed 0, backlog 0
- by publisher: {'cafef': 6, 'vietstock': 2}; by topic: {'appointment': 2, 'board': 1, 'prosecution': 4, 'shareholding': 1}
- chunk totals: {'mentions': 395, 'rule_candidates': 2, 'llm_candidates': 11, 'qa_pass': 1, 'qa_quarantine': 11, 'qa_reject': 0, 'entities_in_candidates': 18, 'candidates_unique': 12, 'chunks': 1}
- graph: nodes(validated) 92, nodes(all) 272, edges by tier {'LEGACY_OFFICIAL': 44, 'QA_PASS': 11, 'QUARANTINE': 126, 'REJECT': 2, 'LEGACY_CANDIDATE': 31}, relation types 12, components {'legacy_official': {'components': 33, 'largest': 4, 'nodes': 74}, 'qa_pass': {'components': 8, 'largest': 4, 'nodes': 19}, 'validated_union(legacy_official+qa_pass)': {'components': 40, 'largest': 4, 'nodes': 92}, 'all_tiers': {'components': 91, 'largest': 14, 'nodes': 272}}, collisions 3
- new edges per 1000 processed articles: {'QA_PASS': 125.0, 'QUARANTINE': 1375.0, 'all_tiers': 1500.0}
- Qwen live calls 20/90000; speed 9.17 art/min; ETA 0.0 h; disk {'free_gb': 297.0, 'campaign_gb': 0.06}
- acquire: {'state': 'COMPLETED', 'pid': 26904, 'alive': False, 'heartbeat_age_s': 787.228527, 'acquired_new': 8, 'counters': {'fetched': 5, 'stored_new': 5, 'failed': 0, 'robots': 0, 'rejected': 0, 'duplicates': 0, 'retries': 0}, 'http_spacing_ok': True, 'last_error': None, 'shortfall': 0, 'exhausted_sources': []}
- process: {'state': 'COMPLETED', 'pid': 25676, 'alive': False, 'heartbeat_age_s': 31.228527, 'chunk': None, 'stage': None, 'articles_per_min': 9.17, 'eta_hours': 0.0, 'qwen_used': 20, 'qwen_budget': 90000, 'last_error': None, 'stop_reason': None}
- neo4j blocker: None
## FINAL STATE: COMPLETED
- all acquired articles were processed
- acquisition reached 8 or was stopped
- Compliance: only sources cleared in config/crawl_compliance.yaml (CafeF, Vietstock); VnEconomy and Bao Dau tu are excluded (written-consent clauses).
- Exports: data/aggregate/export (graph_validated.graphml, graph_all_tiers.graphml, nodes/edges/evidence/collisions CSV), SQLite data/aggregate/staging_graph.sqlite
- Neo4j: validated layer only (QA_PASS); QUARANTINE/REJECT stay in the SQLite/CSV exports. Blocker: None