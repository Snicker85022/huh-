# Taza OS URS — SECURITY cluster
_Exported: 2026-09-19 21:35 | 4 rows_
_Source: Notion Master URS & Specification Registry_

---
## SEC-001 — Voice audio encryption + PII handling + secrets hygiene
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: voice recordings encrypted at rest, geo_location treated as PII, secrets kept out of git entirely.

**Functional Requirement Specification:**  
Voice audio encrypted at rest; geo_location treated as PII; .env never committed to git.

**Failure Behavior:**  
Fallback: root-only access to audio dir.

**Acceptance Criteria:**  
Audio encrypted; .env in .gitignore; no PII in logs

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Voice-audio-encryption-PII-handling-secrets-hygiene-3cfe152fc1998102ac49c41d1b8a96dc_

---
## SEC-002 — Zero public inbound ports; authenticated remote access tunnel
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: N100 has zero inbound ports open on the public internet; all remote access via encrypted, authenticated tunnel.

**Functional Requirement Specification:**  
Remote access security: N100 must have zero inbound ports open on the public internet; all remote traffic arrives via an encrypted, authenticated tunnel (originally specified as WireGuard + Hetzner VPS + Nginx, since superseded by Tailscale per the 2026-07-07 URS addendum — the security model is equivalent: encrypted traffic, zero public inbound, access requires tunnel authentication).

**Acceptance Criteria:**  
NORMAL:
1. Zero inbound ports open on the public internet-facing side of the N100.
2. All remote traffic arrives via the encrypted, authenticated Tailscale tunnel.

EDGE:
3. A new service added later that needs remote access is routed through the existing tunnel by default — doesn't require someone to remember to avoid opening a new public port.

NEGATIVE:
4. An external port scan against the N100's public IP shows zero open ports — verified externally, not just trusted from internal config review.
5. An unauthenticated device cannot join the Tailscale tunnel — authentication is actually enforced, not just configured and assumed working.

SILENT FAILURE:
6. A misconfiguration (e.g. a debug port left open during development, or a router UPnP rule auto-opening a port) would silently violate this requirement without triggering any alert — verify there's periodic external scanning, not a one-time check at launch.
7. Tailscale itself going down/misconfigured must fail closed (no access) not fail open (falls back to some exposed path) — verify this explicitly.

**Verification Method:**  
1) External port scan: run an actual scan against the N100's public-facing IP from outside the network, confirm zero open ports. 2) Auth-bypass test: attempt to reach an internal service without a valid Tailscale identity, confirm rejection. 3) UPnP/router audit: confirm no auto-port-forwarding rules exist on the gateway router (ties to INFRA 8). 4) Recurring scan: establish a periodic (not one-time) external port-scan cadence to catch future drift. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Open Questions:**  
Acceptance Criteria should be rewritten against the live Tailscale architecture during debate (originally written against the now-cancelled WireGuard/Hetzner/Nginx stack).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Zero-public-inbound-ports-authenticated-remote-access-tunnel-3cfe152fc1998171842dda19a39844ee_

---
## SEC-003 — NocoDB authentication + session timeout
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: NocoDB requires a password and times out sessions after 24 hours.

**Functional Requirement Specification:**  
NocoDB authentication: password-protected, 24h session timeout.

**Failure Behavior:**  
Fallback: IP whitelist as additional layer.

**Acceptance Criteria:**  
Login required; idle expires after 24h; failed logins logged

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/NocoDB-authentication-session-timeout-3cfe152fc19981f2b717e44afae4c10f_

---
## SEC-004 — N100 host firewall (UFW) audit
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: N100 firewall verified as default-deny with explicit, scoped allow rules — not just assumed.

**Functional Requirement Specification:**  
N100 host firewall (UFW) audit: verify default-deny inbound with explicit, scoped allow rules — not Ubuntu's default inactive state, and not a stale permissive rule opening an internal-only port (e.g. dashboard) to 0.0.0.0 instead of LAN-only.

**Failure Behavior:**  
Fallback: tunnel-level auth is the primary control — UFW is defense-in-depth.

**Acceptance Criteria:**  
NORMAL:
1. UFW is active (not Ubuntu's default inactive state) with default-deny inbound.
2. Only explicit, scoped allow rules exist — each tied to a documented, necessary service.

EDGE:
3. A LAN-only service (e.g. the health dashboard) is scoped to the LAN subnet specifically, not 0.0.0.0 — confirm this per-rule, not just 'firewall is on.'

NEGATIVE:
4. Any rule that doesn't map to a documented, currently-needed service is flagged and removed — no orphaned permissive rules from earlier debugging sessions.

SILENT FAILURE:
5. This audit item exists specifically because a stale permissive rule (dashboard open to 0.0.0.0 instead of LAN-only) was found before — verify the audit is a repeatable, documented process (checklist or script), not a one-time manual pass that could regress silently after the next config change.
6. UFW being active is not sufficient if a specific rule still permits a wider CIDR than intended — verify each individual rule's scope, not just the overall active/inactive state.

**Verification Method:**  
1) UFW status audit: confirm active with default-deny inbound. 2) Per-rule review: enumerate every allow rule, confirm each maps to a documented necessary service and correct scope (LAN-only vs. any). 3) Regression check: re-run this audit after any future config change as a documented, repeatable process (script or checklist), not ad hoc. 4) External + internal scan cross-check against SEC-002's port scan. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/N100-host-firewall-UFW-audit-3cfe152fc199819badaccf4445ffe8bc_
