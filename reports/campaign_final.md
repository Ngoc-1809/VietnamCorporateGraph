# Campaign summary final (2026-11-02T14:21:53+07:00)

No gold labels exist: PASS/QUARANTINE counts are rule outcomes, NOT precision/recall/F1.

- articles: discovered 49810, downloaded 30380, parsed 30000, processed 12017, deferred 0, failed 90, backlog 17893
- by publisher: {'cafef': 15218, 'vietstock': 14782}; by topic: {'appointment': 1636, 'board': 4655, 'bond': 1740, 'credit': 1137, 'jv_partnership': 744, 'mna': 1830, 'none': 4780, 'prosecution': 5874, 'sanction': 2629, 'shareholding': 3685, 'subsidiary': 1290}
- chunk totals: {'mentions': 491172, 'rule_candidates': 5199, 'llm_candidates': 26088, 'qa_pass': 1657, 'qa_quarantine': 20068, 'qa_reject': 236, 'entities_in_candidates': 23961, 'candidates_unique': 21961, 'chunks': 64}
- graph: nodes(validated) 1885, nodes(all) 15452, edges by tier {'LEGACY_OFFICIAL': 44, 'QA_PASS': 1463, 'QUARANTINE': 19265, 'REJECT': 234, 'LEGACY_CANDIDATE': 31}, relation types 13, components {'legacy_official': {'components': 33, 'largest': 4, 'nodes': 74}, 'qa_pass': {'components': 518, 'largest': 378, 'nodes': 1834}, 'validated_union(legacy_official+qa_pass)': {'components': 532, 'largest': 383, 'nodes': 1885}, 'all_tiers': {'components': 1381, 'largest': 11540, 'nodes': 15452}}, collisions 1759
- new edges per 1000 processed articles: {'QA_PASS': 137.9, 'QUARANTINE': 1670.0, 'REJECT': 19.6, 'all_tiers': 1827.5}
- Qwen live calls 25869/90000; speed 9.28 art/min; ETA 32.1 h; disk {'free_gb': 287.7, 'campaign_gb': 1.35}
- acquire: {'state': 'COMPLETED', 'pid': 25604, 'alive': False, 'heartbeat_age_s': 39195.963606, 'acquired_new': 30000, 'counters': {'fetched': 13983, 'stored_new': 13782, 'failed': 5, 'robots': 0, 'rejected': 19, 'duplicates': 182, 'retries': 8}, 'http_spacing_ok': True, 'last_error': None, 'shortfall': 0, 'exhausted_sources': []}
- process: {'state': 'STOPPED', 'pid': 51632, 'alive': False, 'heartbeat_age_s': 52.964605, 'chunk': None, 'stage': None, 'articles_per_min': 9.28, 'eta_hours': 32.1, 'qwen_used': 25869, 'qwen_budget': 90000, 'last_error': None, 'stop_reason': 'STOP'}
- neo4j blocker: None
## FINAL STATE: STOPPED
- reason: 17893 articles pending
- reason: 90 articles failed
- acquisition reached 30000 or was stopped
- Compliance: only sources cleared in config/crawl_compliance.yaml (CafeF, Vietstock); VnEconomy and Bao Dau tu are excluded (written-consent clauses).
- Exports: data/aggregate/export (graph_validated.graphml, graph_all_tiers.graphml, nodes/edges/evidence/collisions CSV), SQLite data/aggregate/staging_graph.sqlite
- Neo4j: validated layer only (QA_PASS); QUARANTINE/REJECT stay in the SQLite/CSV exports. Blocker: None