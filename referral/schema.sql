-- ============================================================================
-- Taza Spatula Referral Chain — Laser QR Pedigree System
-- Postgres schema. Target: N100 host Postgres (port 5432, DB tazaos, user taza).
--
-- Design (per Notion feature spec "Spatula Referral Chain — Laser QR Pedigree"):
--   * Each gifted spatula carries a laser-burned QR encoding a compact payload
--     + chain_hash. The DB holds the full pedigree tree; the QR is just the key.
--   * chain_hash lets us detect forged/photocopied QRs without a blockchain:
--     a valid scan must match the pre-registered issuance row.
--   * The referral graph IS the influence network. knows_edges adds the broader
--     "who knows who" friendship layer on top of referral parentage.
--
-- All objects live under schema `referral` to keep them isolated from the rest
-- of tazaos. Safe to run repeatedly (idempotent-ish: guards on create).
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS referral;
SET search_path TO referral, public;

-- pgcrypto gives us gen_random_uuid() + digest() for chain hashing.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- parties: every human in the network (customer, lead, or seed referrer).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS party (
    party_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name  text NOT NULL,                 -- "Maria T." (shown on pedigree)
    full_name     text,
    email         text,
    phone         text,
    -- The party who referred this party (nullable = root / walk-in / founder gift).
    referred_by   uuid REFERENCES party(party_id),
    notes         text,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS party_referred_by_idx ON party(referred_by);
CREATE UNIQUE INDEX IF NOT EXISTS party_email_uidx  ON party(lower(email)) WHERE email IS NOT NULL;

-- ---------------------------------------------------------------------------
-- spatula: one row per physical spatula burned. Pre-registered at ENGRAVE time,
-- BEFORE the QR is handed out. This pre-registration is the anti-fraud spine:
-- a screenshot/photocopy cannot mint a new valid issuance_id + chain_hash pair.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS spatula (
    issuance_id   text PRIMARY KEY,              -- short, URL-safe, human-quotable (e.g. TZ-7F3K9Q)
    owner_id      uuid REFERENCES party(party_id), -- who this spatula was gifted to (NULL until claimed)
    parent_issuance_id text REFERENCES spatula(issuance_id), -- the spatula that referred this one
    chain_hash    text NOT NULL,                 -- HMAC over (issuance_id, parent_chain_hash) — see referral_core.py
    depth         integer NOT NULL DEFAULT 0,    -- 0 = seed spatula (no parent)
    status        text NOT NULL DEFAULT 'burned' -- burned | gifted | redeemed | void
                  CHECK (status IN ('burned','gifted','redeemed','void')),
    burned_at     timestamptz NOT NULL DEFAULT now(),
    gifted_at     timestamptz,
    redeemed_at   timestamptz,
    burn_run_id   text,                          -- links to laser burn log / gcode run
    notes         text
);
CREATE INDEX IF NOT EXISTS spatula_parent_idx ON spatula(parent_issuance_id);
CREATE INDEX IF NOT EXISTS spatula_owner_idx  ON spatula(owner_id);
CREATE INDEX IF NOT EXISTS spatula_status_idx ON spatula(status);

-- ---------------------------------------------------------------------------
-- booking: a paid job attributed to a spatula redemption. This is the dollar
-- source for the leaderboard. A referred customer presents their spatula, staff
-- scans it, we record the booking + the 10% discount that was applied.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS booking (
    booking_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id   uuid NOT NULL REFERENCES party(party_id),      -- who booked (the referred friend)
    via_issuance_id text REFERENCES spatula(issuance_id),        -- the spatula they presented
    gross_amount  numeric(12,2) NOT NULL CHECK (gross_amount >= 0), -- pre-discount job value
    discount_pct  numeric(5,2)  NOT NULL DEFAULT 10.00,
    net_amount    numeric(12,2) GENERATED ALWAYS AS
                    (round(gross_amount * (1 - discount_pct/100.0), 2)) STORED,
    square_ref    text,                                          -- Square order/payment id, if linked
    event_date    date,
    booked_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS booking_customer_idx ON booking(customer_id);
CREATE INDEX IF NOT EXISTS booking_via_idx      ON booking(via_issuance_id);
CREATE INDEX IF NOT EXISTS booking_year_idx     ON booking((date_part('year', booked_at)));

-- ---------------------------------------------------------------------------
-- knows_edge: the broader friendship / acquaintance graph — "who knows who".
-- Undirected in meaning; we store canonical (a < b) to avoid dup pairs.
-- Referral parentage auto-seeds a knows_edge, but this layer also holds
-- relationships that are NOT referrals (spouses, coworkers, event guests, etc.)
-- so influence analysis sees the real social fabric, not just the money tree.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knows_edge (
    party_a       uuid NOT NULL REFERENCES party(party_id),
    party_b       uuid NOT NULL REFERENCES party(party_id),
    relationship  text,                          -- 'referred' | 'friend' | 'family' | 'coworker' | 'guest' ...
    weight        numeric(5,2) NOT NULL DEFAULT 1.0,  -- tie strength for influence weighting
    source        text,                          -- how we learned this ('referral','manual','event')
    created_at    timestamptz NOT NULL DEFAULT now(),
    CHECK (party_a <> party_b),
    CHECK (party_a < party_b),                    -- canonical ordering enforces one row per pair
    PRIMARY KEY (party_a, party_b)
);
CREATE INDEX IF NOT EXISTS knows_a_idx ON knows_edge(party_a);
CREATE INDEX IF NOT EXISTS knows_b_idx ON knows_edge(party_b);

-- ---------------------------------------------------------------------------
-- prize_config: single-row knobs for the year-end contest so the policy that
-- decides who wins a real prize (holiday party for 8) is data, not code.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prize_config (
    id            boolean PRIMARY KEY DEFAULT true CHECK (id),   -- enforces single row
    contest_year  integer NOT NULL,
    -- 'direct'  = only revenue from people you personally referred counts
    -- 'subtree' = revenue from your entire downstream referral tree counts (network influence)
    prize_metric  text NOT NULL DEFAULT 'subtree'
                  CHECK (prize_metric IN ('direct','subtree')),
    prize_label   text NOT NULL DEFAULT 'Free holiday party for 8',
    updated_at    timestamptz NOT NULL DEFAULT now()
);

INSERT INTO prize_config (id, contest_year)
VALUES (true, date_part('year', now())::int)
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- burn_log: audit trail of every laser burn the Elidor performed. Capture-now /
-- analyze-later — append only.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS burn_log (
    burn_run_id   text PRIMARY KEY,
    issuance_id   text REFERENCES spatula(issuance_id),
    gcode_path    text,
    serial_port   text,
    grbl_version  text,
    started_at    timestamptz NOT NULL DEFAULT now(),
    finished_at   timestamptz,
    exit_status   text,                          -- 'ok' | 'error' | 'aborted'
    error_text    text
);

-- ---------------------------------------------------------------------------
-- Convenience view: direct referral dollars per referrer for the contest year.
-- "Direct" = bookings by customers whom this party personally referred.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_direct_dollars AS
SELECT r.party_id                         AS referrer_id,
       r.display_name                     AS referrer_name,
       coalesce(sum(b.net_amount), 0)     AS direct_dollars,
       count(DISTINCT c.party_id)         AS direct_referrals
FROM party r
LEFT JOIN party   c ON c.referred_by = r.party_id
LEFT JOIN booking b ON b.customer_id = c.party_id
     AND date_part('year', b.booked_at) = (SELECT contest_year FROM prize_config)
GROUP BY r.party_id, r.display_name;
