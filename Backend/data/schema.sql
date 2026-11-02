IF DB_ID(N'safezone') IS NULL
BEGIN
    CREATE DATABASE safezone;
END
GO

USE safezone;
GO

CREATE TABLE zones (
    id                NVARCHAR(64)   NOT NULL,
    name              NVARCHAR(255)  NOT NULL,
    risk_level        NVARCHAR(16)   NOT NULL CONSTRAINT df_zones_risk DEFAULT 'normal',
    lat               FLOAT          NULL,
    lng               FLOAT          NULL,
    volunteer_group   NVARCHAR(8)    NULL,
    boundary_geojson  NVARCHAR(MAX)  NULL CONSTRAINT chk_zones_geojson CHECK (boundary_geojson IS NULL OR ISJSON(boundary_geojson) = 1),
    created_at        DATETIME2(6)   NOT NULL CONSTRAINT df_zones_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_zones PRIMARY KEY (id)
);
GO

CREATE TABLE people (
    id                 BIGINT         IDENTITY(1,1) NOT NULL,
    phone              NVARCHAR(32)   NOT NULL,
    first_name         NVARCHAR(255)  NULL,
    zone_id            NVARCHAR(64)   NULL,
    lat                FLOAT          NULL,
    lng                FLOAT          NULL,
    is_registered      BIT            NOT NULL CONSTRAINT df_people_registered DEFAULT 0,
    wants_alerts       BIT            NOT NULL CONSTRAINT df_people_alerts DEFAULT 0,
    person_vuln        NVARCHAR(MAX)  NULL CONSTRAINT df_people_vuln DEFAULT '{}' CONSTRAINT chk_people_vuln CHECK (person_vuln IS NULL OR ISJSON(person_vuln) = 1),
    window_open_until  DATETIME2(6)   NULL,
    created_at         DATETIME2(6)   NOT NULL CONSTRAINT df_people_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_people PRIMARY KEY (id),
    CONSTRAINT uq_people_phone UNIQUE (phone),
    CONSTRAINT fk_people_zone FOREIGN KEY (zone_id) REFERENCES zones(id)
);
GO
CREATE INDEX idx_people_zone ON people(zone_id);
GO

CREATE TABLE incidents (
    id                 BIGINT         IDENTITY(1,1) NOT NULL,
    category           NVARCHAR(32)   NOT NULL,
    lat                FLOAT          NULL,
    lng                FLOAT          NULL,
    zone_id            NVARCHAR(64)   NULL,
    location_known     BIT            NOT NULL CONSTRAINT df_incidents_loc_known DEFAULT 0,
    location_source    NVARCHAR(16)   NULL,
    report_count       INT            NOT NULL CONSTRAINT df_incidents_report_count DEFAULT 1,
    confidence         FLOAT          NOT NULL CONSTRAINT df_incidents_confidence DEFAULT 0.6,
    urgency            FLOAT          NOT NULL CONSTRAINT df_incidents_urgency DEFAULT 0.5,
    priority_score     FLOAT          NOT NULL CONSTRAINT df_incidents_priority DEFAULT 0.0,
    status             NVARCHAR(16)   NOT NULL CONSTRAINT df_incidents_status DEFAULT 'open',
    dispatch_status    NVARCHAR(16)   NOT NULL CONSTRAINT df_incidents_dispatch DEFAULT 'none',
    reopened           BIT            NOT NULL CONSTRAINT df_incidents_reopened DEFAULT 0,
    reopen_reason      NVARCHAR(MAX)  NULL,
    first_report_at    DATETIME2(6)   NOT NULL CONSTRAINT df_incidents_first DEFAULT SYSUTCDATETIME(),
    last_update_at     DATETIME2(6)   NOT NULL CONSTRAINT df_incidents_last DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_incidents PRIMARY KEY (id),
    CONSTRAINT chk_incidents_status CHECK (status IN ('open', 'active', 'resolved', 'closed')),
    CONSTRAINT fk_incidents_zone FOREIGN KEY (zone_id) REFERENCES zones(id)
);
GO
CREATE INDEX idx_incidents_status ON incidents(status);
CREATE INDEX idx_incidents_zone ON incidents(zone_id);
CREATE INDEX idx_incidents_priority_score ON incidents(priority_score DESC);
GO

CREATE TABLE reports (
    id                 BIGINT         IDENTITY(1,1) NOT NULL,
    person_id          BIGINT         NULL,
    incident_id        BIGINT         NULL,
    raw_text           NVARCHAR(MAX)  NULL,
    source             NVARCHAR(16)   NOT NULL CONSTRAINT df_reports_source DEFAULT 'whatsapp',
    source_factor      FLOAT          NOT NULL CONSTRAINT df_reports_factor DEFAULT 1.0,
    category           NVARCHAR(32)   NULL,
    lat                FLOAT          NULL,
    lng                FLOAT          NULL,
    zone_id            NVARCHAR(64)   NULL,
    location_known     BIT            NOT NULL CONSTRAINT df_reports_loc_known DEFAULT 0,
    extraction         NVARCHAR(MAX)  NULL CONSTRAINT df_reports_extraction DEFAULT '{}' CONSTRAINT chk_reports_extraction CHECK (extraction IS NULL OR ISJSON(extraction) = 1),
    created_at         DATETIME2(6)   NOT NULL CONSTRAINT df_reports_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_reports PRIMARY KEY (id),
    CONSTRAINT chk_reports_source CHECK (source IN ('whatsapp', 'web')),
    CONSTRAINT fk_reports_person FOREIGN KEY (person_id) REFERENCES people(id),
    CONSTRAINT fk_reports_incident FOREIGN KEY (incident_id) REFERENCES incidents(id),
    CONSTRAINT fk_reports_zone FOREIGN KEY (zone_id) REFERENCES zones(id)
);
GO
CREATE INDEX idx_reports_incident ON reports(incident_id);
CREATE INDEX idx_reports_person ON reports(person_id);
GO

CREATE TABLE cases (
    id                 BIGINT         IDENTITY(1,1) NOT NULL,
    incident_id        BIGINT         NULL,
    person_id          BIGINT         NULL,
    priority_score     FLOAT          NOT NULL CONSTRAINT df_cases_priority DEFAULT 0.0,
    reason             NVARCHAR(MAX)  NULL,
    vuln_summary       NVARCHAR(MAX)  NULL,
    protocol_path      NVARCHAR(MAX)  NULL CONSTRAINT df_cases_protocol DEFAULT '[]' CONSTRAINT chk_cases_protocol CHECK (protocol_path IS NULL OR ISJSON(protocol_path) = 1),
    status             NVARCHAR(16)   NOT NULL CONSTRAINT df_cases_status DEFAULT 'proposed',
    dispatch_status    NVARCHAR(16)   NOT NULL CONSTRAINT df_cases_dispatch DEFAULT 'none',
    reopened           BIT            NOT NULL CONSTRAINT df_cases_reopened DEFAULT 0,
    reopen_reason      NVARCHAR(MAX)  NULL,
    created_at         DATETIME2(6)   NOT NULL CONSTRAINT df_cases_created DEFAULT SYSUTCDATETIME(),
    closed_at          DATETIME2(6)   NULL,
    CONSTRAINT pk_cases PRIMARY KEY (id),
    CONSTRAINT chk_cases_status CHECK (status IN ('proposed', 'approved', 'rejected', 'resolved')),
    CONSTRAINT chk_cases_dispatch_status CHECK (dispatch_status IN (
        'none', 'offered', 'accepted', 'on_way', 'arrived', 'confirmed', 'closed', 'reopened')),
    CONSTRAINT fk_cases_incident FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE,
    CONSTRAINT fk_cases_person FOREIGN KEY (person_id) REFERENCES people(id)
);
GO
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_dispatch_status ON cases(dispatch_status);
CREATE INDEX idx_cases_priority ON cases(priority_score DESC);
GO

CREATE TABLE events (
    id                 BIGINT         IDENTITY(1,1) NOT NULL,
    type               NVARCHAR(64)   NOT NULL,
    case_id            BIGINT         NULL,
    payload            NVARCHAR(MAX)  NOT NULL CONSTRAINT df_events_payload DEFAULT '{}' CONSTRAINT chk_events_payload CHECK (ISJSON(payload) = 1),
    created_at         DATETIME2(6)   NOT NULL CONSTRAINT df_events_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_events PRIMARY KEY (id),
    CONSTRAINT fk_events_case FOREIGN KEY (case_id) REFERENCES cases(id)
);
GO
CREATE INDEX idx_events_type ON events(type);
CREATE INDEX idx_events_case_id ON events(case_id);
CREATE INDEX idx_events_created_at ON events(created_at);
GO

CREATE TABLE volunteers (
    id                 BIGINT         IDENTITY(1,1) NOT NULL,
    name               NVARCHAR(255)  NOT NULL,
    phone              NVARCHAR(32)   NOT NULL,
    zone_ids           NVARCHAR(MAX)  NOT NULL CONSTRAINT df_volunteers_zones DEFAULT '[]' CONSTRAINT chk_volunteers_zones CHECK (ISJSON(zone_ids) = 1),
    capabilities       NVARCHAR(MAX)  NOT NULL CONSTRAINT df_volunteers_caps DEFAULT '[]' CONSTRAINT chk_volunteers_caps CHECK (ISJSON(capabilities) = 1),
    lat                FLOAT          NULL,
    lng                FLOAT          NULL,
    status             NVARCHAR(16)   NOT NULL CONSTRAINT df_volunteers_status DEFAULT 'off_duty',
    window_open_until  DATETIME2(6)   NULL,
    is_demo            BIT            NOT NULL CONSTRAINT df_volunteers_demo DEFAULT 1,
    created_at         DATETIME2(6)   NOT NULL CONSTRAINT df_volunteers_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_volunteers PRIMARY KEY (id),
    CONSTRAINT chk_volunteers_status CHECK (status IN ('off_duty', 'on_duty', 'busy'))
);
GO
CREATE INDEX idx_volunteers_phone ON volunteers(phone);
CREATE INDEX idx_volunteers_status ON volunteers(status);
GO

CREATE TABLE dispatches (
    id                 BIGINT         IDENTITY(1,1) NOT NULL,
    case_id            BIGINT         NOT NULL,
    volunteer_id       BIGINT         NOT NULL,
    ring               INT            NOT NULL CONSTRAINT df_dispatches_ring DEFAULT 1,
    status             NVARCHAR(16)   NOT NULL CONSTRAINT df_dispatches_status DEFAULT 'offered',
    offered_at         DATETIME2(6)   NULL CONSTRAINT df_dispatches_offered DEFAULT SYSUTCDATETIME(),
    accepted_at        DATETIME2(6)   NULL,
    arrived_at         DATETIME2(6)   NULL,
    done_at            DATETIME2(6)   NULL,
    CONSTRAINT pk_dispatches PRIMARY KEY (id),
    CONSTRAINT uq_dispatches_case_volunteer UNIQUE (case_id, volunteer_id),
    CONSTRAINT chk_dispatches_status CHECK (status IN (
        'offered', 'accepted', 'on_way', 'arrived', 'done', 'declined', 'expired')),
    CONSTRAINT fk_dispatches_case FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    CONSTRAINT fk_dispatches_volunteer FOREIGN KEY (volunteer_id) REFERENCES volunteers(id) ON DELETE CASCADE
);
GO
CREATE INDEX idx_dispatches_case ON dispatches(case_id);
CREATE INDEX idx_dispatches_volunteer ON dispatches(volunteer_id);
CREATE INDEX idx_dispatches_status ON dispatches(status);
GO

CREATE TABLE responder_links (
    token              NVARCHAR(128)  NOT NULL,
    case_id            BIGINT         NOT NULL,
    target_label       NVARCHAR(255)  NULL,
    created_at         DATETIME2(6)   NOT NULL CONSTRAINT df_responder_created DEFAULT SYSUTCDATETIME(),
    expires_at         DATETIME2(6)   NOT NULL,
    CONSTRAINT pk_responder_links PRIMARY KEY (token),
    CONSTRAINT fk_responder_links_case FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
);
GO

CREATE TABLE registrations (
    code               NVARCHAR(32)   NOT NULL,
    first_name         NVARCHAR(255)  NOT NULL,
    zone_id            NVARCHAR(64)   NULL,
    phone              NVARCHAR(32)   NULL,
    wants_alerts       BIT            NOT NULL CONSTRAINT df_registrations_alerts DEFAULT 1,
    created_at         DATETIME2(6)   NOT NULL CONSTRAINT df_registrations_created DEFAULT SYSUTCDATETIME(),
    expires_at         DATETIME2(6)   NOT NULL,
    redeemed_at        DATETIME2(6)   NULL,
    CONSTRAINT pk_registrations PRIMARY KEY (code),
    CONSTRAINT fk_registrations_zone FOREIGN KEY (zone_id) REFERENCES zones(id)
);
GO
CREATE INDEX idx_registrations_phone ON registrations(phone);
GO

CREATE TABLE zone_alerts (
    id                 BIGINT         IDENTITY(1,1) NOT NULL,
    incident_id        BIGINT         NOT NULL,
    person_id          BIGINT         NOT NULL,
    zone_id            NVARCHAR(64)   NULL,
    sent_at            DATETIME2(6)   NOT NULL CONSTRAINT df_zone_alerts_sent DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_zone_alerts PRIMARY KEY (id),
    CONSTRAINT uq_zone_alerts_incident_person UNIQUE (incident_id, person_id),
    CONSTRAINT fk_zone_alerts_incident FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE,
    CONSTRAINT fk_zone_alerts_person FOREIGN KEY (person_id) REFERENCES people(id) ON DELETE CASCADE,
    CONSTRAINT fk_zone_alerts_zone FOREIGN KEY (zone_id) REFERENCES zones(id)
);
GO

CREATE TABLE outbox (
    id                 BIGINT         IDENTITY(1,1) NOT NULL,
    to_phone           NVARCHAR(32)   NOT NULL,
    text               NVARCHAR(MAX)  NOT NULL,
    status             NVARCHAR(16)   NULL CONSTRAINT df_outbox_status DEFAULT 'sent',
    mode               NVARCHAR(8)    NOT NULL CONSTRAINT df_outbox_mode DEFAULT 'mock',
    suppressed_reason  NVARCHAR(255)  NULL,
    sent_at            DATETIME2(6)   NOT NULL CONSTRAINT df_outbox_sent DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_outbox PRIMARY KEY (id),
    CONSTRAINT chk_outbox_mode CHECK (mode IN ('mock', 'live'))
);
GO
CREATE INDEX idx_outbox_phone ON outbox(to_phone);
GO
