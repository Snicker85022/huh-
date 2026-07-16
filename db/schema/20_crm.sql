-- ============================================================================
-- Taza OS — CRM / pre-sales pipeline
--   contacts · accounts · leads · opportunities · touchpoints
-- ----------------------------------------------------------------------------
-- PK convention here is UUID (gen_random_uuid()), NOT the BIGINT used by the
-- ops tables. This is forced by the documented field maps: voice_notes and
-- customer_communications (v0.5.0, current) declare uuid FKs to accounts.id,
-- opportunities.id, contacts.id — so the CRM core must be uuid to match 1:1.
--
-- Payer vs inquirer (Nick-confirmed): a CONTACT is a person who reaches out;
-- an ACCOUNT is the paying entity (person OR company). They are separate, and
-- an opportunity points at both — the corporate case where the inquirer isn't
-- the payer is first-class.
--
-- Change history: mutations of dates / venue / PAYER NAME / guest count are
-- reconstructable from audit_log (before/after JSONB). No per-table shadow
-- versioning in v1.
-- ============================================================================
SET search_path TO taza_ops, public;

-- ---- Enums (documented casing preserved to match sources 1:1) --------------
CREATE TYPE taza_ops.account_type       AS ENUM ('individual', 'company');
CREATE TYPE taza_ops.preferred_channel  AS ENUM ('SMS', 'Email', 'WhatsApp', 'Phone');
CREATE TYPE taza_ops.lead_source        AS ENUM (
    'email_hello',        -- hello@tazabistro.com
    'email_tazadelice',   -- tazadelice@gmail.com
    'wix_form', 'phone', 'referral', 'walk_in', 'other'
);
-- Schema Contract v1 §6.2 — do not add values without a contract amendment.
CREATE TYPE taza_ops.lead_status        AS ENUM ('New', 'Active', 'Dormant', 'Converted');
CREATE TYPE taza_ops.lead_category      AS ENUM ('Hot', 'Warm', 'Low', 'Pass');   -- W2 lead scoring
-- Schema Contract v1 §6.1 (Customer Event).
CREATE TYPE taza_ops.opportunity_status AS ENUM ('Open', 'Booked', 'Declined', 'Cancelled');
CREATE TYPE taza_ops.event_type_code    AS ENUM ('FS','DS','MP','PC','HH','PE','CC'); -- Invoice Form Spec §2
CREATE TYPE taza_ops.setup_type         AS ENUM ('Indoor', 'Outdoor', 'Hybrid');       -- W15
CREATE TYPE taza_ops.service_tier       AS ENUM ('None', 'Standard', 'Premium');        -- linens/water
CREATE TYPE taza_ops.conversion_priority AS ENUM ('Hot', 'Warm', 'Low');                -- W6/W8

-- ---- ACCOUNTS (paying entity) ----------------------------------------------
CREATE TABLE taza_ops.accounts (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_type          taza_ops.account_type NOT NULL DEFAULT 'individual',
    display_name          TEXT NOT NULL,
    legal_name            TEXT,
    primary_email         TEXT,
    primary_phone         TEXT,                       -- E.164
    billing_address       TEXT,
    preferred_channel     taza_ops.preferred_channel DEFAULT 'SMS',
    preferred_payment     TEXT,                       -- Card/ACH/Check/Other (Invoice Form §8)
    referral_source       TEXT,
    notes                 TEXT,
    -- External identity / idempotency (Square customer, Wix customer)
    source_system         taza_ops.source_system,
    external_id           TEXT,
    external_updated_at    TIMESTAMPTZ,
    external_payload_hash  TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_system, external_id)
);
CREATE INDEX idx_accounts_email ON taza_ops.accounts (lower(primary_email));
CREATE INDEX idx_accounts_phone ON taza_ops.accounts (primary_phone);
CREATE TRIGGER trg_accounts_updated_at BEFORE UPDATE ON taza_ops.accounts
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- ---- CONTACTS (a person; the inquirer; may belong to an account) -----------
CREATE TABLE taza_ops.contacts (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id            UUID REFERENCES taza_ops.accounts(id) ON DELETE SET NULL,
    first_name            TEXT,
    last_name             TEXT,
    email                 TEXT,
    phone                 TEXT,                       -- E.164
    title                 TEXT,                       -- role at the company (corporate case)
    preferred_channel     taza_ops.preferred_channel DEFAULT 'SMS',
    is_primary            BOOLEAN NOT NULL DEFAULT FALSE, -- primary contact for the account
    notes                 TEXT,
    source_system         taza_ops.source_system,
    external_id           TEXT,
    external_updated_at    TIMESTAMPTZ,
    external_payload_hash  TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_system, external_id)
);
CREATE INDEX idx_contacts_account ON taza_ops.contacts (account_id);
CREATE INDEX idx_contacts_email   ON taza_ops.contacts (lower(email));
CREATE INDEX idx_contacts_phone   ON taza_ops.contacts (phone);
CREATE TRIGGER trg_contacts_updated_at BEFORE UPDATE ON taza_ops.contacts
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- ---- LEADS (inbound inquiry, pre-confirmation) -----------------------------
CREATE TABLE taza_ops.leads (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id            UUID REFERENCES taza_ops.contacts(id) ON DELETE SET NULL,
    account_id            UUID REFERENCES taza_ops.accounts(id) ON DELETE SET NULL,
    source                taza_ops.lead_source NOT NULL,
    status                taza_ops.lead_status NOT NULL DEFAULT 'New',  -- W1 sets New on intake
    inquiry_summary       TEXT,                       -- the raw ask
    -- Early signals captured before an opportunity is formed
    event_type_hint       taza_ops.event_type_code,
    event_date_hint       DATE,
    guest_count_hint      INTEGER,
    -- W2 lead scoring outputs (qwen2.5:7b)
    profit_score          INTEGER CHECK (profit_score BETWEEN 1 AND 5),
    category              taza_ops.lead_category,
    talking_points        TEXT[],
    red_flags             TEXT[],
    context_brief         TEXT,                       -- inbound-triage brief (v2 roadmap)
    converted_opportunity_id UUID,                    -- FK added after opportunities exists
    first_contact_at      TIMESTAMPTZ,
    last_contact_at       TIMESTAMPTZ,                -- drives 14-day Dormant (W6)
    dormant_at            TIMESTAMPTZ,
    converted_at          TIMESTAMPTZ,                -- terminal; human-only (never auto)
    source_system         taza_ops.source_system,
    external_id           TEXT,                       -- Gmail message id / Wix form id
    external_updated_at    TIMESTAMPTZ,
    external_payload_hash  TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_system, external_id)
);
CREATE INDEX idx_leads_status  ON taza_ops.leads (status);
CREATE INDEX idx_leads_contact ON taza_ops.leads (contact_id);
CREATE TRIGGER trg_leads_updated_at BEFORE UPDATE ON taza_ops.leads
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- ---- OPPORTUNITIES (potential Customer Event / gig) ------------------------
CREATE TABLE taza_ops.opportunities (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id            UUID REFERENCES taza_ops.accounts(id) ON DELETE SET NULL,  -- payer (once known)
    primary_contact_id    UUID REFERENCES taza_ops.contacts(id) ON DELETE SET NULL,  -- decision-maker / inquirer
    lead_id               UUID REFERENCES taza_ops.leads(id)    ON DELETE SET NULL,  -- origin
    title                 TEXT,
    status                taza_ops.opportunity_status NOT NULL DEFAULT 'Open',        -- W3 -> Booked on deposit
    event_type            taza_ops.event_type_code,

    -- Event spec (Invoice Form Field Spec §2–4). Times drive conflict detection.
    venue_type            TEXT,                       -- one of 7 documented types; enum TBD (don't fabricate)
    event_address         TEXT,
    departure_address     TEXT,                       -- default = commercial kitchen
    service_date          DATE,
    time_crew_arrival     TIMESTAMPTZ,
    time_event_start      TIMESTAMPTZ,
    time_event_end        TIMESTAMPTZ,
    time_breakdown_complete TIMESTAMPTZ,
    kitchen_departure_time TIMESTAMPTZ,               -- computed: arrival − drive − pack buffer
    guests_adults         INTEGER CHECK (guests_adults BETWEEN 0 AND 500),
    guests_kids           INTEGER DEFAULT 0,
    guests_staff_meals    INTEGER DEFAULT 0,

    setup_type            taza_ops.setup_type,
    tables_required       INTEGER,
    linens_tier           taza_ops.service_tier,
    tableside_water_tier  taza_ops.service_tier,

    -- Bar: mainly subcontracted, needs vendor quotes (Nick)
    bar_service           BOOLEAN NOT NULL DEFAULT FALSE,
    bar_subcontracted     BOOLEAN NOT NULL DEFAULT TRUE,
    bar_vendor            TEXT,
    bar_quote_cents       INTEGER,
    bar_quote_status      TEXT,                       -- requested / received / accepted

    -- Dispatch/logistics
    gate_code             TEXT,
    parking_notes         TEXT,
    offload_notes         TEXT,
    load_in_door          TEXT,
    elevator_required     BOOLEAN,
    stairs_count          INTEGER,
    sla_notes             TEXT,                       -- service-level agreement details

    -- Sales-inference outputs (W6 nightly / W8 post-delivery scoring)
    conversion_readiness_score INTEGER CHECK (conversion_readiness_score BETWEEN 1 AND 5),
    suggested_pitch_angle TEXT,
    priority              taza_ops.conversion_priority,
    follow_up_rank        INTEGER,
    next_action_suggestion TEXT,
    optimal_followup_window_days INTEGER,
    upsell_angle          TEXT,
    inference_confidence  INTEGER CHECK (inference_confidence BETWEEN 0 AND 100),

    booked_at             TIMESTAMPTZ,
    event_delivered_at    TIMESTAMPTZ,
    declined_at           TIMESTAMPTZ,
    cancelled_at          TIMESTAMPTZ,
    source_system         taza_ops.source_system,
    external_id           TEXT,
    external_updated_at    TIMESTAMPTZ,
    external_payload_hash  TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_system, external_id)
);
CREATE INDEX idx_opps_status   ON taza_ops.opportunities (status);
CREATE INDEX idx_opps_account  ON taza_ops.opportunities (account_id);
-- Advisory date/time conflict detection is app-level and ALWAYS overridable
-- (Nick). No hard exclusion constraint — double-booking is flagged, not blocked.
CREATE INDEX idx_opps_service_date ON taza_ops.opportunities (service_date)
    WHERE status IN ('Open', 'Booked');
CREATE TRIGGER trg_opps_updated_at BEFORE UPDATE ON taza_ops.opportunities
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- Back-fill the forward FK from leads now that opportunities exists.
ALTER TABLE taza_ops.leads
    ADD CONSTRAINT fk_leads_converted_opportunity
    FOREIGN KEY (converted_opportunity_id)
    REFERENCES taza_ops.opportunities(id) ON DELETE SET NULL;

-- ---- TOUCHPOINTS (human + automated interactions) --------------------------
CREATE TYPE taza_ops.touchpoint_type AS ENUM
    ('call', 'email', 'sms', 'whatsapp', 'meeting', 'site_visit', 'follow_up', 'note');
CREATE TYPE taza_ops.comm_direction  AS ENUM ('Inbound', 'Outbound');

CREATE TABLE taza_ops.touchpoints (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id        UUID REFERENCES taza_ops.accounts(id)      ON DELETE SET NULL,
    contact_id        UUID REFERENCES taza_ops.contacts(id)      ON DELETE SET NULL,
    opportunity_id    UUID REFERENCES taza_ops.opportunities(id) ON DELETE SET NULL,
    lead_id           UUID REFERENCES taza_ops.leads(id)         ON DELETE SET NULL,
    touchpoint_type   taza_ops.touchpoint_type NOT NULL,
    direction         taza_ops.comm_direction,
    occurred_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    summary           TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_touchpoints_opp     ON taza_ops.touchpoints (opportunity_id);
CREATE INDEX idx_touchpoints_account ON taza_ops.touchpoints (account_id);
CREATE TRIGGER trg_touchpoints_updated_at BEFORE UPDATE ON taza_ops.touchpoints
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();
