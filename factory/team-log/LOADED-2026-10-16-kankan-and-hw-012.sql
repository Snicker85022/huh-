-- ══════════════════════════════════════════════════════════════════════════════
-- SPEC LOAD — 2026-10-16
-- Loads two approved proposals into spec.taza_os_user_requirement_specifications.
--
-- Source proposals (verbatim; these are the record):
--   factory/team-log/SPEC-PROPOSAL-kanban-task-lifecycle.md  -> URS-KANBAN-006
--   factory/team-log/SPEC-PROPOSAL-lg-tv-hw-012.md           -> HW-012
--
-- NOT loaded: the checklist-on-LG-TV feature row. Its spec_id (URS-TV-CHECKLIST-001)
-- was rejected during the build because TV-* is the Android/ADB fleet namespace; it
-- belongs under URS-DISP-007. It is held until it is rewritten against the facts
-- learned on 2026-10-15 (PROD-38, the kanban close contract, the SSAP control path).
--
-- STATUS = 'Spec Drafted': these are loaded to stop them getting lost, not because
-- they are final. Nick re-debates them once each app has a good spec.
-- Idempotent: guarded by a NOT EXISTS on spec_id, so re-running is safe.
--
-- is_current is set EXPLICITLY to true. Every existing row is 't' (291 of 291) and the
-- spec-export mirror filters `where is_current`, which SQL excludes NULL from — so a row
-- inserted without it would be invisible to the CSV. Learned the hard way on this load.
-- ══════════════════════════════════════════════════════════════════════════════

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- URS-KANBAN-006  Mom's Kanban Game — task lifecycle, close contract, bus publication
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO spec.taza_os_user_requirement_specifications (
  spec_id, name, status, priority, release, record_type, domain,
  determinism_class, required_for_release, is_current,
  user_requirement, functional_requirement,
  ac_normal, ac_edge, ac_negative, ac_silent_failure, ac_challenge, ac_block,
  verification_methods, vm_count, vm_auto_count, vm_nick_count,
  failure_behavior, dependency_notes, open_questions,
  consumes, consumed_by,
  atomic_requirement, intent_user_need, inputs, outputs,
  trigger_condition, invariants, out_of_scope, maintenance_requirements,
  external_dependencies, rationale, failure_mode_addressed, source
)
SELECT
  'URS-KANBAN-006',
  'Kanban task lifecycle, canonical close contract, and bus publication',
  'Spec Drafted', 'P0', 'V1.0', 'Atomic Requirement', 'Production Core',
  'D', 'YES', true,

  'Need: closing any card — confirm/prep/cook/portion/pack/stage/deliver/flag — behaves the same underneath: one canonical TaskCloseEvent through one router, exactly one committed event on the intercom, traceable back to its gig/invoice. No card kind gets bespoke persistence; no close is invisible to the LG TV display, scoring, or any future consumer.',

  'The kanban app (server_kanban.py, port 9003) shall implement PROD-38: one frozen TaskCloseEvent dataclass and one TaskCloseRouter. All 8 deck _kind values route through that single router; no per-kind POST endpoint and no bespoke front-end close path remain. The router (a) validates the close, (b) writes the app''s state exactly once, and (c) emits exactly one task.closed event to public.system_events in the SAME transaction as the state write, so a failed close emits nothing and a retry emits no duplicate. The event payload carries task_id, close_kind, close_method, crew_id, invoice. The app shall register its topics in public.event_topics and shall refuse to start if they are not registered (fail closed).',

  E'1. Close a card of any of the 8 kinds -> exactly one task.closed row in system_events with the required payload keys, and no duplicate write on the state store.\n2. Prep/portion close also carries kind-specific fields (leftover_qty, leftover_unit, location, photo_path) inside the event payload - no separate table write is required.',

  E'3. Same close retried with the same correlation_id -> no second system_events row, no duplicated consumer effect (consumer de-dups on correlation_id).\n4. Two cards closed concurrently -> both commit, both publish, no interleaving corruption.',

  E'5. Close with no/insufficient PIN -> rejected before any write; no event emitted.\n6. Close a card already done -> rejected by the state machine; validate_event() rejects task.closed because to_state=done is not reachable from from_state=done.',

  E'7. The state write succeeds but the system_events INSERT fails (dead connection) -> whole transaction rolls back; caller gets an error; the card is NOT done. No half-close.\n8. validate_event() rejects the emit (bad payload/state) -> the transaction rolls back; the card is NOT done. Rejections land in event_rejects (quarantine), never silently dropped.',

  E'9. 20 cards closed in rapid succession during service transition -> all 20 committed and published; system_events.id monotonic; no reject rows for task.closed.',

  E'10. task.closed is not in event_topics -> the server refuses to start (startup pre-flight), so no close can be attempted against a missing topic.\n11. entity_table is left NULL for these topics because the intercom referential check is hardcoded to square_invoice_id (see DEF-3). Attempting entity_table=task_cards is a build error.',

  E'VM1 AUTO: per-close_kind (8) unit test emits a well-formed event with all required payload keys.\nVM2 AUTO: integration test - POST close -> one system_events row + state committed atomically.\nVM3 AUTO: idempotency - same correlation_id retried -> single row everywhere.\nVM4 AUTO: state machine - closing a done card -> HTTP 409, zero row changes.\nVM5 AUTO: startup gate - with topic unregistered, server refuses to start.\nVM6 NICK: live close on the board -> event visible in system_events via psql, payload correct.',

  6, 5, 1,

  'A close that fails at any step (validate, state write, emit) rolls back entirely: the card is not done and no event exists. The server fails closed at startup if its topics are unregistered. Bus rejections are quarantined in event_rejects, never dropped silently.',

  E'PROD-38 (TaskCloseEvent + TaskCloseRouter) is the contract this implements; neither the dataclass nor the router exists in code today.\nPROD-20 + URS-EVENT-001: the bus, validate_event(), block_event_mutation(), and the event_topics registry are live and verified.\nURS-KANBAN-001 (hand/table/done) is enforced client-side only; there is no server-side state machine today.\nURS-KANBAN-002 (accountable handoff) is NOT implemented: the board has no crew login (taza-card-table.html:640) and confirmLay() checks only if(!pending||pinBuf.length<4) return; (taza-card-table.html:992) - any 4 digits close a card. crew_member is hardcoded "Crew".\nURS-KANBAN-005 (commit-then-emit, exactly one correlated event) is the core this row makes buildable.',

  E'See the DEFICIT REGISTER in the source proposal (DEF-1..DEF-10) and section 8 OPEN QUESTIONS. Chief open items: (a) owner_module for the new topics - proposed taza-kanban; (b) whether crew_pin_hash stays in the app private store rather than the bus payload; (c) whether URS-KANBAN-002 (crew accountability) gets its own fix row; (d) status of public.task_cards (verified orphaned: rows ids 31-40 from 2026-10-09, live deck ids 101-128, nothing writes it); (e) who owns "gig is complete" - no spec_id today.',

  'PROD-38, PROD-20, URS-EVENT-001, URS-KANBAN-001, URS-KANBAN-002, URS-KANBAN-005',
  'checklist display (checklist_app.py -> DEBT-007/PROD-20), SSB-001/SSB-003/KIT-007 (TV display and staleness). Scoring has NO spec_id today - DEFICIT, see DEF-9.',

  'Closing any card of any kind in the kanban game commits the task state and publishes exactly one task.closed event carrying task_id, close_kind, close_method, crew_id and invoice.',
  'The crew needs a card to close the same reliable way regardless of kind, so that every downstream consumer (display, scoring, inventory) can trust one event.',
  'Card close (task_id, close_kind, close_method, crew_id, PIN, kind-specific fields: qty/unit/location/photo).',
  'One task.closed event per commit on public.system_events; the app private state written in the same transaction.',
  'A card is dragged hand->table (started) and then closed table->done.',
  'No close is invisible; no close is double-counted; a failed close emits nothing; the server fails closed if its topics are unregistered.',
  'Scoring UI, game points, and the LG TV render are downstream consumers, not part of this row.',
  'The topic registrations must exist in public.event_topics before the app will start.',
  'Postgres (tazaos): public.system_events, public.event_topics, public.event_rejects. The live server /home/taza/kitchen/server_kanban.py ports :9003.',
  'PROD-38 states one trusted close mechanism rather than bespoke close logic per module, each of which can hide its own bugs. Today only prep-kind cards persist anything, and the INSERT drops the invoice - so the kanban game cannot currently feed any downstream consumer.',
  'A card close that is lost, duplicated, or invisible to downstream consumers - including the LG TV checklist display.',
  'Nick 2026-10-16 (from the fusion team proposal SPEC-PROPOSAL-kanban-task-lifecycle.md)'
WHERE NOT EXISTS (
  SELECT 1 FROM spec.taza_os_user_requirement_specifications WHERE spec_id = 'URS-KANBAN-006'
);

COMMIT;

-- ─────────────────────────────────────────────────────────────────────────────
-- HW-012  LG webOS TV OLED55B7A — kitchen checklist display (device + control surface)
-- ─────────────────────────────────────────────────────────────────────────────
BEGIN;

INSERT INTO spec.taza_os_user_requirement_specifications (
  spec_id, name, status, priority, release, record_type, domain,
  determinism_class, required_for_release, is_current,
  user_requirement, functional_requirement,
  ac_normal, ac_edge, ac_negative, ac_silent_failure, ac_challenge, ac_block,
  verification_methods, vm_count, vm_auto_count, vm_nick_count,
  failure_behavior, dependency_notes, open_questions,
  consumes, consumed_by,
  atomic_requirement, intent_user_need, inputs, outputs,
  trigger_condition, invariants, out_of_scope, maintenance_requirements,
  external_dependencies, rationale, failure_mode_addressed, source,
  hw_make, hw_model, hw_mpn, hw_connectivity, hw_purchase_date, hw_purchase_source
)
SELECT
  'HW-012',
  'LG webOS TV OLED55B7A (kitchen checklist display)',
  'Spec Drafted', 'P1', 'V1.0', 'Atomic Requirement', 'System Infrastructure',
  'HUM', 'NO', true,

  'Need: a dedicated kitchen display panel — an LG webOS OLED TV — that the system can reach and control over the LAN without anyone touching it, so the checklist (and later displays) can be shown on it remotely.',

  E'DEVICE IDENTITY: LG webOS TV OLED55B7A, 55-inch OLED, model year 2022, OS webOS 22 (webOS 7.0). FriendlyName "[LG] webOS TV OLED55B7A".\n\nPLACEMENT / ROLE: the dedicated kitchen checklist display panel. Wired Ethernet 192.168.2.127 (MAC 78:5d:c8:00:82:0b) is the PRIMARY path; Wi-Fi 192.168.2.137 is fallback ONLY, and running on Wi-Fi must raise an alert (never silent).\n\nCONTROL SURFACE: SSAP (lge-com:service:webos-second-screen) over WebSocket on TCP 3000 (HTTP/1.1 101 upgrade). Authenticated by one paired client-key, issued after an on-screen accept by Nick; key file /home/taza/repo/secrets/lg_tv.json on n100 only. Never in the repo, never in this row.\n\nVERIFIED WORKING (probe 2026-10-15):\n  - Launch a page: ssap://system.launcher/launch {id:"com.webos.app.browser", params:{target:"<url>"}} -> returnValue:true. Nick saw the page appear.\n  - Read foreground app: ssap://com.webos.applicationManager/getForegroundAppInfo -> {"appId":"com.webos.app.browser"}.\n  - Power state: ssap://com.webos.service.tvpower/power/getPowerState -> {"state":"Active"}.\n  - App inventory: ssap://com.webos.applicationManager/listLaunchPoints -> 30 apps.\n\nNOT AVAILABLE (explicit constraints a later spec must not assume):\n  - No ADB: port 5555 closed (webOS is not Android).\n  - No Developer Mode: SSH 9922 closed, so ares-cli is unavailable.\n  - CDP 9998 answers but lists NO targets (an inspector, not a launcher).\n  - No wake-on-LAN endpoint over SSAP (404).\n  - turnOnScreen/turnOffScreen EXIST (401, not 404) but the permission name is unknown (12 spellings tried, all 401). Do NOT spec a dependency on it; the proven heal is re-issuing the launch.\n  - Screensaver dims the panel but does NOT kill the browser: content survives and getForegroundAppInfo still reports the browser. Nick disabled "turn off after 2 hours" and enabled "Mobile TV On" on the device.',

  'SSAP over WebSocket :3000 from n100 proves control: launching com.webos.app.browser with a target URL returns returnValue:true and Nick sees the page; getForegroundAppInfo reports appId=com.webos.app.browser; getPowerState reports state=Active.',

  'Ethernet to 192.168.2.127 drops — the TV falls back to Wi-Fi (.137) and an alert fires naming the fallback; when Ethernet returns, the controller uses the wired path again with no manual step.',

  'Any dependency on ADB (5555), ares-cli / Developer Mode (9922), CDP-as-launcher (9998), or SSAP turnOnScreen -> BLOCKED. These are proven unavailable on this device; re-issuing the launch is the only heal.',

  'Controller believes the page is up while the TV shows something else (launch silently rejected, or foreground app changed) -> detected when getForegroundAppInfo returns appId != com.webos.app.browser, then healed by re-issuing the launch.',

  'After a factory reset or clearing the paired-client list, SSAP auth fails -> the controller detects the auth failure and raises an alert naming the on-screen re-pair step, never silently retrying a dead pairing.',

  '',

  E'1) [AUTO] SSAP launch + read + power from n100 against 192.168.2.127:3000.\n   Evidence: grep "SSAP_LAUNCH|returnValue:true|appId.*com.webos.app.browser|\"state\":\"Active\"" /var/log/taza/lg-tv-control.log | tail -6\n   (expect launch returnValue:true, appId=com.webos.app.browser, state=Active)\n2) [AUTO] Control code has zero forbidden-dependency usage.\n   Evidence: grep -rn "5555|9922|ares-cli|devMode|turnOnScreen" product/ --include="*.py" --include="*.sh" --include="*.ts"\n   (expect zero hits in executable paths)\n3) [AUTO] Wired-primary enforcement: .127 is primary; any active .137 raises an alert.\n   Evidence: grep "LG_TV_WIFI_FALLBACK|LG_TV_ACTIVE_IFACE" /var/log/taza/lg-tv-control.log | tail -3\n   (expect .127 wired primary; .137 active -> alert line present)\n4) [NICK] On-screen: Nick sees the launched page on the TV after a fresh launch.',

  4, 3, 1,

  E'- TV unreachable or browser not foreground: detect via getForegroundAppInfo; heal by re-issuing system.launcher/launch. Never assume screen-wake.\n- Active path is Wi-Fi (.137) instead of Ethernet (.127): raise an alert naming the fallback (fallback is fail-visible, never a silent state).\n- Pairing lost (factory reset or cleared paired-client list): SSAP auth fails; alert naming the on-screen re-pair step.',

  E'- This row is the DEVICE. The checklist-display feature is a separate spec (proposed URS-DISP-007) which will CONSUME this row; no content/layout/staleness/status-feed decisions belong here.\n- A later spec must not assume ADB, Developer Mode, CDP-as-launcher, or SSAP screen-wake on this device.\n- Related existing specs: TV-007 (TV watchdog + Chrome auto-relaunch) covers the Android/TV fleet via ADB. THIS TV has NO ADB and must not be governed by TV-007.\n- HW-005 (Kitchen Ethernet Switching and Cabling) is the network path this device depends on.',

  'Q1: required_for_release is proposed NO (additive display; paper remains the safety net) - confirm. Q2: hw_purchase_date and hw_purchase_source are unverified (the device pre-exists the deployment records) - supply if known. Q3: confirm the proposed consumer spec id is URS-DISP-007 (not URS-TV-CHECKLIST-001, which collides with the Android/TV namespace).',

  'HW-005',
  'URS-DISP-007 (proposed — the checklist-display spec consumes this device)',

  'The kitchen shall have one dedicated, remotely-controllable display panel — the LG webOS TV OLED55B7A at 192.168.2.127 — reachable from n100 over SSAP on TCP 3000 for launching and verifying content, with Ethernet as the primary path and Wi-Fi as a fail-visible fallback.',
  'The crew needs one glance at a screen that no one has to walk over and start.',
  'SSAP commands from n100 (launch, getForegroundAppInfo, getPowerState, listLaunchPoints).',
  'A rendered page on the TV panel; a readable foreground-app id for the controller.',
  'The controller issues an SSAP launch, then verifies via getForegroundAppInfo.',
  'Ethernet is primary; a Wi-Fi fallback is always visible as an alert; the credential never leaves n100; no dependency on ADB, Developer Mode, CDP-as-launcher or SSAP screen-wake.',
  'What the TV displays (checklist content, layout, staleness rules) - that is URS-DISP-007, not this row.',
  E'- Keep the paired client-key only at /home/taza/repo/secrets/lg_tv.json on n100; never commit it, never inline it.\n- Factory reset or clearing the paired-client list breaks pairing -> re-pair on-screen and replace the key file.\n- IPs are DHCP-reserved; if the reservation changes, update the controller wired-primary config.',

  'The LG SSAP service on the TV (webOS); no cloud dependency. n100 LAN reachability to 192.168.2.127:3000.',
  'The paper checklist is a single point of truth that exists only on paper. A dedicated, remotely-controlled panel lets the same information be shown without crew effort, and it is the only kitchen surface whose control path (SSAP) is proven independent of Android/ADB.',
  'A kitchen display that cannot be reached or restarted remotely, forcing someone to walk over and touch it.',
  'Nick 2026-10-16 (from the fusion team proposal SPEC-PROPOSAL-lg-tv-hw-012.md)',

  'LG', 'OLED55B7A', 'OLED55B7A (no suffix verified; friendlyName is "webOS TV OLED55B7A")',
  'Ethernet RJ45 primary (192.168.2.127), Wi-Fi fallback only (192.168.2.137); control via SSAP over WebSocket TCP 3000',
  '', ''
WHERE NOT EXISTS (
  SELECT 1 FROM spec.taza_os_user_requirement_specifications WHERE spec_id = 'HW-012'
);

COMMIT;
