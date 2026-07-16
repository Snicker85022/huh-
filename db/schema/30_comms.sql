-- ============================================================================
-- Taza OS — Communications & capture
--   exceptions · voice_notes · customer_communications
-- ----------------------------------------------------------------------------
-- voice_notes and customer_communications are transcribed VERBATIM from the
-- documented field maps (📊 Data Schemas & Field Maps v0.5.0 — the only two
-- fully-populated tables). Types, defaults, nullability, enum value sets, and
-- FK targets match the spec 1:1. Text columns whose spec lists an enum set are
-- kept as TEXT (as documented) with a CHECK to enforce the set — this maps
-- cleanly to a NocoDB single-select.
-- ============================================================================
SET search_path TO taza_ops, public;

-- ---- EXCEPTIONS (gentle-failure queue, D-006) ------------------------------
-- Errors route here instead of crashing; humans review. voice_notes.exception_ref
-- points here. resolution_reasoning is OPTIONAL — see the override-policy note
-- in docs/schema-contract.md (Sandra's routine overrides capture no "why" by
-- design, HAI-001; Nick's deltas + exception resolutions may).
CREATE TABLE taza_ops.exceptions (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_workflow      TEXT,                 -- e.g. 'W7', 'square_import'
    entity_type          TEXT,                 -- table the failure relates to
    entity_id            TEXT,
    exception_type       TEXT,                 -- classification
    message              TEXT NOT NULL,
    stack_trace          TEXT,
    retry_status         TEXT DEFAULT 'pending', -- pending / retrying / gave_up / resolved
    is_resolved          BOOLEAN NOT NULL DEFAULT FALSE,
    resolution_reasoning TEXT,                 -- optional "why this way not that" capture
    resolved_by          TEXT,                 -- crew PIN / operator
    resolved_at          TIMESTAMPTZ,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_exceptions_unresolved ON taza_ops.exceptions (created_at) WHERE is_resolved = FALSE;
CREATE TRIGGER trg_exceptions_updated_at BEFORE UPDATE ON taza_ops.exceptions
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- ---- VOICE_NOTES (Sandra's brain-dumps → overnight LLM parse → promote) -----
CREATE TABLE taza_ops.voice_notes (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    captured_at            TIMESTAMPTZ NOT NULL,       -- when recorded (may predate upload)
    speaker                TEXT NOT NULL DEFAULT 'Sandra'
                             CHECK (speaker IN ('Sandra','Nick','Edgar','Other')),
    capture_source         TEXT NOT NULL
                             CHECK (capture_source IN
                               ('Sandra mic','Phone call','In-person','Site walkthrough','SMS dictation','Other')),
    audio_file_url         TEXT,                       -- null if typed
    transcript             TEXT NOT NULL,              -- Whisper/Sherpa-ONNX; Sandra may edit
    transcript_confidence  NUMERIC CHECK (transcript_confidence BETWEEN 0.00 AND 1.00),
    linked_account_id      UUID REFERENCES taza_ops.accounts(id)      ON DELETE SET NULL,
    linked_opportunity_id  UUID REFERENCES taza_ops.opportunities(id) ON DELETE SET NULL,
    linked_contact_id      UUID REFERENCES taza_ops.contacts(id)      ON DELETE SET NULL,
    intent_tags            TEXT[]
                             CHECK (intent_tags <@ ARRAY[
                               'Lead-update','Opportunity-update','Touchpoint-log','Followup',
                               'Menu','Logistics','Personal-note','Other']::text[]),
    extracted_entities     JSONB,                      -- dates, $, guest counts, dietary, ...
    processing_status      TEXT NOT NULL DEFAULT 'New'
                             CHECK (processing_status IN ('New','Parsed','Promoted','Error')),
    llm_model_version      TEXT,                       -- e.g. qwen2.5:14b@2026-05-21
    manual_review_required BOOLEAN NOT NULL DEFAULT FALSE,  -- true if confidence < 0.85
    promoted_to_records    JSONB,                      -- {accounts:[id], opportunities:[id], ...}
    geo_location           TEXT,                       -- PII; site-walkthrough memos
    exception_ref          UUID REFERENCES taza_ops.exceptions(id) ON DELETE SET NULL,
    processed_at           TIMESTAMPTZ,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_vn_created         ON taza_ops.voice_notes (created_at);
CREATE INDEX idx_vn_captured        ON taza_ops.voice_notes (captured_at);
CREATE INDEX idx_vn_status          ON taza_ops.voice_notes (processing_status);
CREATE INDEX idx_vn_review          ON taza_ops.voice_notes (manual_review_required) WHERE manual_review_required;
CREATE INDEX idx_vn_account         ON taza_ops.voice_notes (linked_account_id);
CREATE INDEX idx_vn_opportunity     ON taza_ops.voice_notes (linked_opportunity_id);
CREATE INDEX idx_vn_contact         ON taza_ops.voice_notes (linked_contact_id);
CREATE TRIGGER trg_voice_notes_updated_at BEFORE UPDATE ON taza_ops.voice_notes
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- ---- CUSTOMER_COMMUNICATIONS (SMS/Email/WhatsApp/Phone log) -----------------
CREATE TABLE taza_ops.customer_communications (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    customer_id           UUID NOT NULL REFERENCES taza_ops.accounts(id) ON DELETE CASCADE,
    channel               TEXT NOT NULL CHECK (channel IN ('SMS','Email','WhatsApp','Phone')),
    direction             TEXT NOT NULL CHECK (direction IN ('Inbound','Outbound')),
    message_body          TEXT NOT NULL,              -- PII; retention policy applies
    message_subject       TEXT,                       -- null for SMS/WhatsApp
    message_status        TEXT NOT NULL DEFAULT 'Sent'
                            CHECK (message_status IN
                              ('Sent','Delivered','Read','Failed','Replied','Bounced')),
    external_id           TEXT UNIQUE,                -- Twilio SID / Gmail msg id (webhook dedup)
    external_provider     TEXT NOT NULL
                            CHECK (external_provider IN ('Twilio','Gmail','Square Messages')),
    linked_invoice_id     UUID,                       -- FK added in 40_financial.sql
    linked_opportunity_id UUID REFERENCES taza_ops.opportunities(id) ON DELETE SET NULL,
    linked_touchpoint_id  UUID REFERENCES taza_ops.touchpoints(id)   ON DELETE SET NULL,
    sent_at               TIMESTAMPTZ,
    delivered_at          TIMESTAMPTZ,
    read_at               TIMESTAMPTZ,
    cost_cents            INTEGER DEFAULT 0,          -- per-message cost (Twilio budget)
    media_urls            TEXT[],                     -- MMS / attachments
    metadata              JSONB,                      -- provider-specific
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_cc_customer     ON taza_ops.customer_communications (customer_id);
CREATE INDEX idx_cc_channel      ON taza_ops.customer_communications (channel);
CREATE INDEX idx_cc_direction    ON taza_ops.customer_communications (direction);
CREATE INDEX idx_cc_status       ON taza_ops.customer_communications (message_status);
CREATE INDEX idx_cc_provider     ON taza_ops.customer_communications (external_provider);
CREATE INDEX idx_cc_sent         ON taza_ops.customer_communications (sent_at);
CREATE INDEX idx_cc_opportunity  ON taza_ops.customer_communications (linked_opportunity_id);
CREATE TRIGGER trg_cc_updated_at BEFORE UPDATE ON taza_ops.customer_communications
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();
