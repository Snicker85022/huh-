#!/usr/bin/env python3
"""Extract every cross-cluster [[SPEC:...]] reference from master-urs.md."""

import re, sys

# Read the file
with open('/home/taza/repo/master-urs.md', 'r') as f:
    lines = f.readlines()

# Map each spec to its cluster
# Cluster boundaries from pass1-findings.md
cluster_map = {
    # kit-legacy
    "KIT-001": "kit-legacy", "KIT-005": "kit-legacy", "KIT-007": "kit-legacy",
    "KIT-008": "kit-legacy", "KIT-010": "kit-legacy", "KIT-012": "kit-legacy",
    "KIT-013": "kit-legacy", "KIT-014": "kit-legacy", "KIT-015": "kit-legacy",
    "KIT-017": "kit-legacy", "KIT-020": "kit-legacy", "KIT-022": "kit-legacy",
    "KIT-023": "kit-legacy",
    # ai
    "AI-001": "ai", "AI-002": "ai", "AI-003": "ai", "AI-004": "ai",
    "AI-005": "ai", "AI-006": "ai", "AI-007": "ai", "AI-008": "ai",
    # alexa
    "ALC-001": "alexa", "ALC-002": "alexa", "ALC-003": "alexa",
    "ALC-004": "alexa", "ALC-005": "alexa",
    # catalog
    "CAT-001": "catalog", "CAT-002": "catalog", "CAT-003": "catalog",
    "CAT-004": "catalog", "CAT-005": "catalog", "CAT-006": "catalog",
    # req-ci
    "REQ-CI-001": "req-ci", "REQ-CI-002": "req-ci", "REQ-CI-003": "req-ci",
    # crew
    "URS-CREW-001": "crew", "URS-CREW-002": "crew", "URS-CREW-003": "crew",
    "URS-CREW-004": "crew",
    # culture
    "CULT-001": "culture", "CULT-002": "culture", "CULT-003": "culture",
    "CULT-004": "culture", "CULT-005": "culture", "CULT-006": "culture",
    "CULT-007": "culture", "CULT-008": "culture", "CULT-009": "culture",
    "CULT-010": "culture", "CULT-011": "culture", "CULT-012": "culture",
    # cx
    "CX-001": "cx", "CX-002": "cx", "CX-003": "cx", "CX-004": "cx",
    "CX-005": "cx", "CX-006": "cx", "CX-007": "cx",
    # db
    "DB-001": "db", "DB-002": "db", "DB-003": "db", "DB-004": "db",
    # doc
    "DOC-001": "doc", "DOC-002": "doc", "DOC-003": "doc", "DOC-004": "doc",
    # epr
    "EPR-001": "epr", "EPR-002": "epr", "EPR-003": "epr", "EPR-004": "epr",
    "EPR-007": "epr",
    # hai
    "HAI-001": "hai", "HAI-002": "hai", "HAI-003": "hai", "HAI-004": "hai",
    "HAI-005": "hai",
    # hw
    "HW-001": "hw", "HW-002": "hw", "HW-003": "hw", "HW-004": "hw",
    "HW-005": "hw", "HW-006": "hw", "HW-007": "hw", "HW-008": "hw",
    "HW-009": "hw", "HW-010": "hw",
    # infra
    "INFRA-001": "infra", "INFRA-002": "infra", "INFRA-003": "infra",
    "INFRA-004": "infra", "INFRA-005": "infra", "INFRA-006": "infra",
    "INFRA-007": "infra", "INFRA-008": "infra", "INFRA-009": "infra",
    # int
    "INT-001": "int", "INT-003": "int", "INT-004": "int", "INT-005": "int",
    "INT-006": "int", "INT-007": "int",
    # disp
    "URS-DISP-001": "disp", "URS-DISP-002": "disp", "URS-DISP-003": "disp",
    "URS-DISP-004": "disp", "URS-DISP-005": "disp", "URS-DISP-006": "disp",
    "URS-DISP-PKG": "disp",
    # event
    "URS-EVENT-001": "event", "URS-EVENT-002": "event",
    # health
    "URS-HEALTH-001": "health", "URS-HEALTH-002": "health",
    "URS-HEALTH-003": "health", "URS-HEALTH-004": "health",
    "URS-HEALTH-005": "health",
    # inv
    "URS-INV-001": "inv", "URS-INV-002": "inv", "URS-INV-003": "inv",
    "URS-INV-004": "inv", "URS-INV-005": "inv",
    # kanban
    "URS-KANBAN-001": "kanban", "URS-KANBAN-002": "kanban",
    "URS-KANBAN-003": "kanban", "URS-KANBAN-004": "kanban",
    "URS-KANBAN-005": "kanban",
    # label
    "URS-LABEL-001": "label", "URS-LABEL-003": "label",
    "URS-LABEL-004": "label", "URS-LABEL-005": "label",
    "URS-LABEL-006": "label",
    # lkl
    "URS-LKL-001": "lkl", "URS-LKL-002": "lkl", "URS-LKL-003": "lkl",
    "URS-LKL-004": "lkl", "URS-LKL-PKG": "lkl",
    # mt
    "MT-001": "mt", "MT-002": "mt",
    # mobile
    "URS-MOB-001": "mobile", "URS-MOB-002": "mobile", "URS-MOB-003": "mobile",
    "URS-MOB-004": "mobile", "URS-MOB-005": "mobile", "URS-MOB-PKG": "mobile",
    # ops
    "OPS-001": "ops", "OPS-002": "ops", "OPS-003": "ops", "OPS-004": "ops",
    # planner
    "URS-PLAN-001": "planner", "URS-PLAN-002": "planner",
    "URS-PLAN-003": "planner", "URS-PLAN-004": "planner",
    "URS-PLAN-005": "planner", "URS-PLAN-006": "planner",
    "URS-PLAN-007": "planner", "URS-PLAN-008": "planner",
    "URS-PLAN-PKG": "planner",
    # screens
    "SCREEN-01": "screens", "SCREEN-02": "screens", "SCREEN-03": "screens",
    "SCREEN-04": "screens", "SCREEN-05": "screens", "SCREEN-06": "screens",
    "SCREEN-07": "screens", "SCREEN-08": "screens", "SCREEN-09": "screens",
    "SCREEN-10": "screens", "SCREEN-11": "screens", "SCREEN-12": "screens",
    # sec
    "SEC-001": "sec", "SEC-002": "sec", "SEC-003": "sec", "SEC-004": "sec",
    # sw
    "SW-001": "sw", "SW-002": "sw", "SW-003": "sw", "SW-004": "sw",
    "SW-005": "sw", "SW-006": "sw", "SW-007": "sw", "SW-008": "sw",
    "SW-009": "sw", "SW-010": "sw", "SW-011": "sw", "SW-012": "sw",
    "SW-013": "sw",
    # ssb
    "SSB-001": "ssb", "SSB-002": "ssb", "SSB-003": "ssb", "SSB-004": "ssb",
    "SSB-005": "ssb", "SSB-006": "ssb", "SSB-007": "ssb",
    # tv
    "TV-001": "tv", "TV-002": "tv", "TV-003": "tv", "TV-004": "tv",
    "TV-005": "tv", "TV-006": "tv", "TV-007": "tv", "TV-011": "tv",
    "TV-012": "tv",
    # ui
    "UI-001": "ui", "UI-002": "ui", "UI-003": "ui", "UI-004": "ui",
    "UI-005": "ui",
    # call
    "URS-CALL-001": "call", "URS-CALL-002": "call", "URS-CALL-003": "call",
    "URS-CALL-004": "call", "URS-CALL-005": "call", "URS-CALL-006": "call",
    # crm
    "URS-CRM-001": "crm", "URS-CRM-002": "crm", "URS-CRM-003": "crm",
    "URS-CRM-004": "crm", "URS-CRM-005": "crm", "URS-CRM-006": "crm",
    "URS-CRM-007": "crm", "URS-CRM-008": "crm", "URS-CRM-009": "crm",
    # sys-intent
    "URS-SYS-INTENT-001": "sys-intent",
    # v1.0-ig
    "V1.0-IG": "v1.0-ig",
    # workflows — numbered W*
    "W1": "workflows", "W2": "workflows", "W3": "workflows", "W4": "workflows",
    "W5": "workflows", "W6": "workflows", "W7": "workflows", "W8": "workflows",
    "W9": "workflows", "W10": "workflows", "W11": "workflows", "W12": "workflows",
    "W13": "workflows", "W14": "workflows", "W15": "workflows",
    # PROD — product specs
    "PROD-01": "prod", "PROD-02": "prod", "PROD-03": "prod",
    "PROD-04": "prod", "PROD-05-V2": "prod", "PROD-06": "prod",
    "PROD-07": "prod", "PROD-08": "prod", "PROD-09": "prod",
    "PROD-10": "prod", "PROD-11": "prod", "PROD-12": "prod",
    "PROD-13": "prod", "PROD-14": "prod", "PROD-15": "prod",
    "PROD-16": "prod", "PROD-16-V2": "prod", "PROD-17": "prod",
    "PROD-18": "prod", "PROD-19": "prod", "PROD-20": "prod",
    "PROD-21": "prod", "PROD-22": "prod", "PROD-23": "prod",
    "PROD-24": "prod", "PROD-25": "prod", "PROD-26": "prod",
    "PROD-27": "prod", "PROD-28": "prod", "PROD-29": "prod",
    "PROD-30": "prod", "PROD-31": "prod",
    "PROD-37": "prod",
    "URS-KIT-103": "kit-legacy",
    "URS-KIT-107": "kit-legacy",
    "V2-FEAT-006": "v2-feat",
    "V2-PROD-16": "prod",
}

# For specs not in the map, try to infer from prefix
def cluster_of(spec):
    if spec in cluster_map:
        return cluster_map[spec]
    if spec.startswith("PROD-"):
        return "prod"
    if spec.startswith("V2-"):
        return "v2"
    if spec.startswith("W") and spec[1:].isdigit():
        return "workflows"
    if spec.startswith("URS-KIT-"):
        return "kit-legacy"
    if spec.startswith("URS-"):
        # URS- but unknown
        return "unknown-urs"
    return "unknown"

# Find every spec heading line, determine which spec owns each line
line_owner = {}  # line_number -> spec_id
current_spec = None
spec_heading_line = {}

# Match spec headings: ## <SPEC-ID> — Title
heading_pattern = re.compile(r'^## ([A-Z][A-Za-z0-9_-]+(?:-\d+)?(?:-V\d+)?(?:-PKG)?)\s*[—–-]')

for i, line in enumerate(lines):
    m = heading_pattern.match(line)
    if m:
        spec = m.group(1)
        # clean trailing whitespace from spec
        spec = spec.strip()
        if spec:
            current_spec = spec
            spec_heading_line[spec] = i
    line_owner[i] = current_spec

# Now find all [[SPEC:...]] references and classify
ref_pattern = re.compile(r'\[\[SPEC:([A-Za-z0-9_-]+)\]\]')

# Collect seams by source_spec -> (target_spec, line_number, context_line)
seams_raw = []

for i, line in enumerate(lines):
    source_spec = line_owner.get(i)
    if not source_spec:
        continue
    source_cluster = cluster_of(source_spec)
    for m in ref_pattern.finditer(line):
        target_spec = m.group(1)
        target_cluster = cluster_of(target_spec)
        if source_spec == target_spec:
            continue  # self-reference, skip
        seams_raw.append((i, source_spec, source_cluster, target_spec, target_cluster, line.strip()[:200]))

# Summarize
print("=== ALL CROSS-CLUSTER SEAMS ===")
print(f"{'Source Spec':<20} {'Source Cluster':<15} {'Target Spec':<20} {'Target Cluster':<15} {'Direction':<10} {'Line':<6} Context")
print("="*130)

cross_cluster = []
for (i, src_spec, src_cluster, tgt_spec, tgt_cluster, ctx) in seams_raw:
    if src_cluster != tgt_cluster:
        direction = "depends-on"
        cross_cluster.append((src_spec, src_cluster, tgt_spec, tgt_cluster, direction, i, ctx))
        print(f"{src_spec:<20} {src_cluster:<15} {tgt_spec:<20} {tgt_cluster:<15} {direction:<10} {i:<6} {ctx}")

print(f"\n\nTotal cross-cluster refs found: {len(cross_cluster)}")
print(f"\nUnique spec pairs:")
pairs = set((s[0], s[2]) for s in cross_cluster)
for pair in sorted(pairs):
    print(f"  {pair[0]} → {pair[1]}")

print(f"\n\nUnique spec-pair + clusters:")
pair_clusters = set((s[0], s[1], s[2], s[3]) for s in cross_cluster)
for pc in sorted(pair_clusters):
    print(f"  {pc[0]} ({pc[1]}) → {pc[2]} ({pc[3]})")