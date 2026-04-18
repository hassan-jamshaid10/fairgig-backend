-- =============================================================================
-- FairGig — Master Database Schema
-- PostgreSQL 17+
-- =============================================================================

-- UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- SCHEMAS
-- auth_svc     : user identity, roles, and authentication
-- earnings_svc : shift records, pay data, and screenshot verification
-- grievance_svc: worker grievance submissions and tracking
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS auth_svc;
CREATE SCHEMA IF NOT EXISTS earnings_svc;
CREATE SCHEMA IF NOT EXISTS grievance_svc;

COMMENT ON SCHEMA auth_svc      IS 'User identity and authentication — managed by the Auth service';
COMMENT ON SCHEMA earnings_svc  IS 'Shift earnings records and screenshot verification — managed by the Earnings service';
COMMENT ON SCHEMA grievance_svc IS 'Worker grievance submissions and status tracking — managed by the Grievance service';

-- =============================================================================
-- auth_svc.users
-- Central user table shared (via FK) by all other schemas.
-- =============================================================================

CREATE TABLE auth_svc.users (
    id              UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255)  NOT NULL UNIQUE,
    password_hash   TEXT          NOT NULL,
    role            VARCHAR(20)   NOT NULL
                        CHECK (role IN ('Worker', 'Verifier', 'Advocate')),
    full_name       VARCHAR(255)  NOT NULL,
    phone           VARCHAR(30),
    city_zone       VARCHAR(100),
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  auth_svc.users              IS 'All platform users — Workers, Verifiers, and Advocates';
COMMENT ON COLUMN auth_svc.users.role         IS 'Worker: submits shifts | Verifier: reviews screenshots | Advocate: manages grievances';
COMMENT ON COLUMN auth_svc.users.city_zone    IS 'Anonymised geographic zone used for aggregate analytics';
COMMENT ON COLUMN auth_svc.users.password_hash IS 'bcrypt hash — plain-text password is never stored';

-- =============================================================================
-- earnings_svc.shifts
-- One row per work shift reported by a Worker.
-- =============================================================================

CREATE TABLE earnings_svc.shifts (
    id                   UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id            UUID         NOT NULL
                             REFERENCES auth_svc.users(id) ON DELETE CASCADE,
    platform             VARCHAR(100) NOT NULL,
    shift_date           DATE         NOT NULL,
    hours_worked         NUMERIC(6,2) NOT NULL CHECK (hours_worked > 0),
    gross_earned         NUMERIC(10,2) NOT NULL CHECK (gross_earned >= 0),
    platform_deductions  NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (platform_deductions >= 0),
    net_received         NUMERIC(10,2) NOT NULL CHECK (net_received >= 0),
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  earnings_svc.shifts                    IS 'Individual shift records submitted by Workers';
COMMENT ON COLUMN earnings_svc.shifts.platform           IS 'Gig platform name e.g. Uber, Careem, Bykea';
COMMENT ON COLUMN earnings_svc.shifts.gross_earned       IS 'Total fare/earnings before any deductions';
COMMENT ON COLUMN earnings_svc.shifts.platform_deductions IS 'Commission or fees taken by the platform';
COMMENT ON COLUMN earnings_svc.shifts.net_received       IS 'Amount actually received by the Worker';

-- =============================================================================
-- earnings_svc.screenshots
-- Screenshot evidence attached to a shift for Verifier review.
-- =============================================================================

CREATE TABLE earnings_svc.screenshots (
    id           UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    shift_id     UUID         NOT NULL
                     REFERENCES earnings_svc.shifts(id) ON DELETE CASCADE,
    verifier_id  UUID
                     REFERENCES auth_svc.users(id) ON DELETE SET NULL,
    image_url    TEXT         NOT NULL,
    status       VARCHAR(20)  NOT NULL DEFAULT 'Pending'
                     CHECK (status IN ('Pending', 'Confirmed', 'Flagged', 'Unverifiable')),
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  earnings_svc.screenshots             IS 'Pay-slip screenshot uploaded alongside a shift record';
COMMENT ON COLUMN earnings_svc.screenshots.verifier_id IS 'Verifier who reviewed this screenshot — NULL until assigned';
COMMENT ON COLUMN earnings_svc.screenshots.status      IS 'Pending → Confirmed | Flagged | Unverifiable';

-- =============================================================================
-- grievance_svc.grievances
-- Worker-submitted complaints about platform practices.
-- =============================================================================

CREATE TABLE grievance_svc.grievances (
    id           UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id    UUID         NOT NULL
                     REFERENCES auth_svc.users(id) ON DELETE CASCADE,
    platform     VARCHAR(100) NOT NULL,
    category     VARCHAR(100) NOT NULL,
    description  TEXT         NOT NULL,
    status       VARCHAR(50)  NOT NULL DEFAULT 'Open',
    is_anonymous BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  grievance_svc.grievances              IS 'Grievances filed by Workers against gig platforms';
COMMENT ON COLUMN grievance_svc.grievances.category     IS 'e.g. Unfair Deduction, Account Suspension, Safety, Payment Delay';
COMMENT ON COLUMN grievance_svc.grievances.is_anonymous IS 'When TRUE the worker identity is hidden in public-facing views';
COMMENT ON COLUMN grievance_svc.grievances.status       IS 'Open → Under Review → Resolved | Dismissed';

-- =============================================================================
-- earnings_svc.anonymized_shifts  (VIEW)
-- Safe read-only view for analytics — worker_id, name, and email are excluded.
-- city_zone is kept for geographic aggregation but is not personally identifiable.
-- =============================================================================

CREATE OR REPLACE VIEW earnings_svc.anonymized_shifts AS
SELECT
    s.city_zone,
    sh.platform,
    sh.shift_date,
    sh.hours_worked,
    sh.gross_earned,
    sh.platform_deductions,
    sh.net_received
FROM earnings_svc.shifts  sh
JOIN auth_svc.users        s  ON s.id = sh.worker_id;

COMMENT ON VIEW earnings_svc.anonymized_shifts IS
    'Privacy-safe view for the Analytics service — excludes worker_id, full_name, email, and phone';










/* =============================================================================
   grievance_svc.grievance_comments
   Stores flat community comments on a specific grievance.
   ============================================================================= */

CREATE TABLE grievance_svc.grievance_comments (
    id           UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    grievance_id UUID         NOT NULL
                              REFERENCES grievance_svc.grievances(id) ON DELETE CASCADE,
    worker_id    UUID         NOT NULL
                              REFERENCES auth_svc.users(id) ON DELETE CASCADE,
    comment_text TEXT         NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE grievance_svc.grievance_comments IS 'Community replies to a specific grievance post';

/* =============================================================================
   grievance_svc.grievance_tags
   Stores hashtags linked to grievances for the trending algorithm.
   ============================================================================= */

CREATE TABLE grievance_svc.grievance_tags (
    id           UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    grievance_id UUID         NOT NULL
                              REFERENCES grievance_svc.grievances(id) ON DELETE CASCADE,
    tag_name     VARCHAR(50)  NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


COMMENT ON TABLE grievance_svc.grievance_tags IS 'Hashtags used for clustering and trending topics';




























/* =============================================================================
   1. auth_svc.roles
   Defines the available roles in the system.
   ============================================================================= */
CREATE TABLE auth_svc.roles (
    id   UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE
);

/* Insert the 3 required roles immediately */
INSERT INTO auth_svc.roles (name) VALUES ('Worker'), ('Verifier'), ('Advocate');

/* =============================================================================
   2. auth_svc.user_roles
   The mapping table (junction table) that connects users to roles.
   ============================================================================= */
CREATE TABLE auth_svc.user_roles (
    user_id UUID NOT NULL REFERENCES auth_svc.users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES auth_svc.roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

COMMENT ON TABLE auth_svc.user_roles IS 'Mapping table: allows one user to have multiple roles';

/* =============================================================================
   3. Cleanup the Users Table
   We no longer need the 'role' column in the users table because of the mapping.
   ============================================================================= */
ALTER TABLE auth_svc.users DROP COLUMN IF EXISTS role;