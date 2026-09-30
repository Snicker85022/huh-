# Pass 0 — Edge / Reciprocity Findings

Registry: 287 specs. Canonical edges: 121 (17 mirrored, 104 one-way).

## ONE_WAY edges

- CAT-001 → CAT-002  [ONE_WAY_OUT]  (catalog → catalog)
- CAT-001 → PROD-16-V2  [ONE_WAY_OUT]  (catalog → prod)
- CAT-001 → SW-011  [ONE_WAY_OUT]  (catalog → software)
- CAT-001 → URS-KIT-102  [ONE_WAY_IN]  (catalog → kit)
- CAT-001 → W15  [ONE_WAY_OUT]  (catalog → workflows)
- CAT-001 → W7  [ONE_WAY_OUT]  (catalog → workflows)
- CAT-001 → W9  [ONE_WAY_OUT]  (catalog → workflows)
- KIT-001 → URS-LKL-001  [ONE_WAY_IN]  (kit-legacy → lkl)
- PROD-01 → PROD-24  [ONE_WAY_IN]  (prod → prod)
- PROD-01 → PROD-25  [ONE_WAY_IN]  (prod → prod)
- PROD-01 → URS-DISP-002  [ONE_WAY_IN]  (prod → display)
- PROD-01 → URS-KANBAN-001  [ONE_WAY_IN]  (prod → kanban)
- PROD-01 → URS-KIT-103  [ONE_WAY_IN]  (prod → kit)
- PROD-02 → PROD-24  [ONE_WAY_IN]  (prod → prod)
- PROD-02 → PROD-36  [ONE_WAY_IN]  (prod → prod)
- PROD-02 → PROD-37  [ONE_WAY_IN]  (prod → prod)
- PROD-03 → PROD-01  [ONE_WAY_OUT]  (prod → prod)
- PROD-04 → URS-DISP-003  [ONE_WAY_IN]  (prod → display)
- PROD-04 → URS-DISP-004  [ONE_WAY_IN]  (prod → display)
- PROD-05-V2 → URS-MOB-002  [ONE_WAY_IN]  (prod → mobile)
- PROD-06 → PROD-05  [ONE_WAY_IN]  (prod → prod)
- PROD-09 → PROD-05-V2  [ONE_WAY_IN]  (prod → prod)
- PROD-09 → PROD-16  [ONE_WAY_IN]  (prod → prod)
- PROD-09 → PROD-16-V2  [ONE_WAY_IN]  (prod → prod)
- PROD-10 → PROD-18  [ONE_WAY_IN]  (prod → prod)
- PROD-14 → PROD-02  [ONE_WAY_OUT]  (prod → prod)
- PROD-14 → PROD-04  [ONE_WAY_OUT]  (prod → prod)
- PROD-14 → PROD-07  [ONE_WAY_OUT]  (prod → prod)
- PROD-15 → PROD-03  [ONE_WAY_OUT]  (prod → prod)
- PROD-15 → PROD-09  [ONE_WAY_OUT]  (prod → prod)
- PROD-16 → PROD-16-V2  [ONE_WAY_IN]  (prod → prod)
- PROD-16-V2 → PROD-02  [ONE_WAY_OUT]  (prod → prod)
- PROD-17 → PROD-06  [ONE_WAY_OUT]  (prod → prod)
- PROD-17 → PROD-07  [ONE_WAY_OUT]  (prod → prod)
- PROD-18 → PROD-07  [ONE_WAY_OUT]  (prod → prod)
- PROD-18 → PROD-09  [ONE_WAY_OUT]  (prod → prod)
- PROD-18 → PROD-16  [ONE_WAY_OUT]  (prod → prod)
- PROD-19 → PROD-04  [ONE_WAY_OUT]  (prod → prod)
- PROD-20 → PROD-04  [ONE_WAY_OUT]  (prod → prod)
- PROD-20 → PROD-24  [ONE_WAY_IN]  (prod → prod)
- PROD-21 → PROD-07  [ONE_WAY_OUT]  (prod → prod)
- PROD-21 → PROD-22  [ONE_WAY_OUT]  (prod → prod)
- PROD-21 → W1  [ONE_WAY_OUT]  (prod → workflows)
- PROD-21 → W2  [ONE_WAY_OUT]  (prod → workflows)
- PROD-21 → W6  [ONE_WAY_OUT]  (prod → workflows)
- PROD-22 → PROD-04  [ONE_WAY_OUT]  (prod → prod)
- PROD-22 → W6  [ONE_WAY_OUT]  (prod → workflows)
- PROD-23 → PROD-04  [ONE_WAY_OUT]  (prod → prod)
- PROD-23 → PROD-22  [ONE_WAY_OUT]  (prod → prod)
- PROD-23 → URS-MOB-003  [ONE_WAY_IN]  (prod → mobile)
- PROD-24 → PROD-10  [ONE_WAY_OUT]  (prod → prod)
- PROD-25 → PROD-04  [ONE_WAY_OUT]  (prod → prod)
- PROD-25 → PROD-22  [ONE_WAY_OUT]  (prod → prod)
- PROD-25 → URS-EVENT-002  [ONE_WAY_IN]  (prod → event)
- PROD-26 → PROD-10  [ONE_WAY_OUT]  (prod → prod)
- PROD-26 → PROD-20  [ONE_WAY_OUT]  (prod → prod)
- PROD-26 → PROD-24  [ONE_WAY_OUT]  (prod → prod)
- PROD-26 → PROD-25  [ONE_WAY_OUT]  (prod → prod)
- PROD-26 → PROD-28  [ONE_WAY_IN]  (prod → prod)
- PROD-26 → SW-001  [ONE_WAY_OUT]  (prod → software)
- PROD-27 → PROD-01  [ONE_WAY_OUT]  (prod → prod)
- PROD-27 → PROD-20  [ONE_WAY_OUT]  (prod → prod)
- PROD-27 → PROD-22  [ONE_WAY_OUT]  (prod → prod)
- PROD-28 → PROD-04  [ONE_WAY_OUT]  (prod → prod)
- PROD-28 → PROD-25  [ONE_WAY_OUT]  (prod → prod)
- PROD-34 → PROD-04  [ONE_WAY_OUT]  (prod → prod)
- PROD-34 → PROD-25  [ONE_WAY_OUT]  (prod → prod)
- PROD-34 → PROD-37  [ONE_WAY_IN]  (prod → prod)
- PROD-37 → PROD-02  [ONE_WAY_OUT]  (prod → prod)
- PROD-37 → PROD-36  [ONE_WAY_OUT]  (prod → prod)
- PROD-38 → PROD-02  [ONE_WAY_OUT]  (prod → prod)
- PROD-38 → PROD-19  [ONE_WAY_OUT]  (prod → prod)
- PROD-38 → PROD-20  [ONE_WAY_OUT]  (prod → prod)
- PROD-38 → PROD-22  [ONE_WAY_OUT]  (prod → prod)
- PROD-38 → PROD-36  [ONE_WAY_OUT]  (prod → prod)
- PROD-38 → PROD-37  [ONE_WAY_OUT]  (prod → prod)
- URS-CREW-002 → URS-CREW-001  [ONE_WAY_IN]  (crew → crew)
- URS-DISP-002 → PROD-04  [ONE_WAY_OUT]  (display → prod)
- URS-DISP-002 → URS-DISP-003  [ONE_WAY_IN]  (display → display)
- URS-DISP-002 → URS-DISP-004  [ONE_WAY_IN]  (display → display)
- URS-DISP-002 → URS-DISP-005  [ONE_WAY_IN]  (display → display)
- URS-EVENT-001 → URS-EVENT-002  [ONE_WAY_IN]  (event → event)
- URS-EVENT-001 → URS-KANBAN-005  [ONE_WAY_IN]  (event → kanban)
- URS-EVENT-001 → URS-LKL-004  [ONE_WAY_IN]  (event → lkl)
- URS-HEALTH-001 → URS-HEALTH-005  [ONE_WAY_OUT]  (health → health)
- URS-INV-001 → URS-INV-005  [ONE_WAY_IN]  (inventory → inventory)
- URS-INV-003 → URS-INV-004  [ONE_WAY_IN]  (inventory → inventory)
- URS-INV-003 → URS-LABEL-001  [ONE_WAY_IN]  (inventory → label)
- URS-KIT-101 → PROD-22  [ONE_WAY_OUT]  (kit → prod)
- URS-KIT-102 → PROD-22  [ONE_WAY_OUT]  (kit → prod)
- URS-KIT-105 → URS-KIT-106  [ONE_WAY_IN]  (kit → kit)
- URS-LABEL-001 → URS-LABEL-006  [ONE_WAY_IN]  (label → label)
- URS-LABEL-006 → URS-LABEL-005  [ONE_WAY_OUT]  (label → label)
- URS-LKL-002 → URS-LKL-004  [ONE_WAY_IN]  (lkl → lkl)
- V1.0-IG → W7  [ONE_WAY_OUT]  (uncategorized → workflows)
- W1 → W6  [ONE_WAY_IN]  (workflows → workflows)
- W15 → PROD-04  [ONE_WAY_IN]  (workflows → prod)
- W15 → URS-KIT-103  [ONE_WAY_IN]  (workflows → kit)
- W2 → PROD-25  [ONE_WAY_IN]  (workflows → prod)
- W2 → W3  [ONE_WAY_IN]  (workflows → workflows)
- W4 → W3  [ONE_WAY_IN]  (workflows → workflows)
- W4 → W6  [ONE_WAY_IN]  (workflows → workflows)
- W4 → W7  [ONE_WAY_IN]  (workflows → workflows)
- W9 → W15  [ONE_WAY_IN]  (workflows → workflows)

## Short-form references (resolved to canonical IDs)

- `CREW-002` → ['URS-CREW-002']
- `CREW-003` → ['URS-CREW-003']
- `CREW-004` → ['URS-CREW-004']
- `DISP-002` → ['URS-DISP-002']
- `EVENT-001` → ['URS-EVENT-001']
- `HEALTH-005` → ['URS-HEALTH-005']
- `INV-001` → ['URS-INV-001']
- `INV-003` → ['URS-INV-003']
- `KANBAN-002` → ['URS-KANBAN-002']
- `KANBAN-005` → ['URS-KANBAN-005']
- `KIT-101` → ['URS-KIT-101']
- `KIT-102` → ['URS-KIT-102']
- `KIT-103` → ['URS-KIT-103']
- `KIT-104` → ['URS-KIT-104']
- `KIT-105` → ['URS-KIT-105']
- `LABEL-001` → ['URS-LABEL-001']
- `LABEL-005` → ['URS-LABEL-005']
- `LKL-001` → ['URS-LKL-001']
- `LKL-002` → ['URS-LKL-002']

## Dangling references (no canonical ID exists)

- PROD-02 → `WIC-1-3`: ne]-[Unit]-[Shelf] validated vs master (e.g. WIC-1-3), missing elements list
- PROD-36 → `PROD-33`: future barcode/NPU predictive-prep-counting (PROD-33) as an alternate input path
- SW-013 → `SW-016`: Append-only telemetry tables. Feeds SW-016 replay-DOE + TQAI scorer, SW-019 retrospecti
- SW-013 → `SW-019`: bles. Feeds SW-016 replay-DOE + TQAI scorer, SW-019 retrospective mining
- W9 → `V2-FEAT-006`: alog_version cursor. Feeds W7 (RAG lookups), V2-FEAT-006 Backward Scheduler

## Legacy alias families (need canonical mapping)

