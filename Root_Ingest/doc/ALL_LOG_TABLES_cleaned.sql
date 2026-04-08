-- ===== ERROR_LOG_DATA_cleaned.sql =====
-- Ingest-friendly schema reference for LLM/RAG
-- Source table: dbo.ERROR_LOG_DATA
-- Removed: USE/GO, ANSI settings, lock escalation, fillfactor, partition/storage placement
-- Purpose: equipment error/alarm log records
-- Note: descriptions below are inferred from column names and DDL only.

CREATE TABLE dbo.ERROR_LOG_DATA (
    EQPID       varchar(20)  NOT NULL,                  -- Equipment ID
    MODULEID    varchar(30)  NOT NULL,                  -- Module ID within equipment
    EVENTTIME   datetime2(3) NOT NULL,                  -- Event occurrence timestamp
    UNIT        varchar(20)  NOT NULL,                  -- Unit or chamber identifier
    STEP        varchar(20)  NULL,                      -- Process step name or code
    GLASSID     varchar(20)  NULL,                      -- Primary glass/substrate ID
    GLASSID2    varchar(20)  NULL,                      -- Secondary glass/substrate ID
    LOTID       varchar(20)  NULL,                      -- Production lot ID
    HOSTPPID    varchar(20)  NULL,                      -- Host recipe / process program ID
    EQPPPID     varchar(20)  NULL,                      -- Equipment recipe / process program ID
    ACTION      varchar(5)   NOT NULL,                  -- Alarm action code (exact code set should be confirmed)
    ALARMID     varchar(6)   NOT NULL,                  -- Alarm identifier/code
    ALARMTEXT   varchar(100) NULL,                      -- Alarm description text
    FILENAME    varchar(64)  NULL,                      -- Source file name or ingest file name
    CREATETIME  datetime2(7) NULL DEFAULT getdate(),    -- Row creation / insert timestamp

    CONSTRAINT ERROR_LOG_DATA_PK PRIMARY KEY (
        EQPID,
        MODULEID,
        EVENTTIME,
        UNIT,
        ACTION,
        ALARMID
    )
);

-- Recommended semantic notes for retrieval:
-- 1) EVENTTIME is usually the main time filter column for event-range questions.
-- 2) CREATETIME is the record creation time, not necessarily the event occurrence time.
-- 3) ACTION and ALARMID together are key dimensions for grouping or deduplication.


-- ===== EVENT_LOG_DATA_cleaned.sql =====
-- Ingest-friendly schema reference for LLM/RAG
-- Source table: dbo.EVENT_LOG_DATA
-- Removed: USE/GO, ANSI settings, lock escalation, fillfactor, partition/storage placement
-- Purpose: equipment event log records
-- Note: descriptions below are inferred from column names and DDL only.

CREATE TABLE dbo.EVENT_LOG_DATA (
    EQPID       varchar(20)  NOT NULL,                  -- Equipment ID
    MODULEID    varchar(30)  NOT NULL,                  -- Module ID within equipment
    EVENTTIME   datetime2(3) NOT NULL,                  -- Event occurrence timestamp
    UNIT        varchar(20)  NOT NULL,                  -- Unit or chamber identifier
    STEP        varchar(20)  NULL,                      -- Process step name or code
    GLASSID     varchar(20)  NULL,                      -- Primary glass/substrate ID
    GLASSID2    varchar(20)  NULL,                      -- Secondary glass/substrate ID
    LOTID       varchar(20)  NULL,                      -- Production lot ID
    HOSTPPID    varchar(20)  NULL,                      -- Host recipe / process program ID
    EQPPPID     varchar(20)  NULL,                      -- Equipment recipe / process program ID
    EVENTID     varchar(20)  NOT NULL,                  -- Event identifier/code
    COL1        varchar(30)  NOT NULL,                  -- Generic event attribute #1 (business meaning must be confirmed; part of PK)
    COL2        varchar(30)  NOT NULL,                  -- Generic event attribute #2 (business meaning must be confirmed; part of PK)
    COL3        varchar(30)  NULL,                      -- Generic event attribute #3 (business meaning must be confirmed)
    COL4        varchar(30)  NULL,                      -- Generic event attribute #4 (business meaning must be confirmed)
    COL5        varchar(30)  NULL,                      -- Generic event attribute #5 (business meaning must be confirmed)
    FILENAME    varchar(64)  NULL,                      -- Source file name or ingest file name
    CREATETIME  datetime2(7) NULL DEFAULT getdate(),    -- Row creation / insert timestamp

    CONSTRAINT EVENT_LOG_DATA_PK PRIMARY KEY (
        EQPID,
        MODULEID,
        EVENTTIME,
        UNIT,
        EVENTID,
        COL1,
        COL2
    )
);

-- Recommended semantic notes for retrieval:
-- 1) EVENTTIME is usually the main time filter column for event-range questions.
-- 2) CREATETIME is the record creation time, not necessarily the event occurrence time.
-- 3) COL1 and COL2 are part of the primary key, so their exact business meaning is important and should be documented separately.
-- 4) Before production use, map COL1~COL5 to domain names if an interface spec exists.


-- ===== WARNING_LOG_DATA_cleaned.sql =====
-- Ingest-friendly schema reference for LLM/RAG
-- Source table: dbo.WARNING_LOG_DATA
-- Removed: USE/GO, ANSI settings, lock escalation, fillfactor, partition/storage placement
-- Purpose: equipment warning log records
-- Note: descriptions below are inferred from column names and DDL only.

CREATE TABLE dbo.WARNING_LOG_DATA (
    EQPID       varchar(20)  NOT NULL,                  -- Equipment ID
    MODULEID    varchar(30)  NOT NULL,                  -- Module ID within equipment
    EVENTTIME   datetime2(3) NOT NULL,                  -- Event occurrence timestamp
    UNIT        varchar(20)  NOT NULL,                  -- Unit or chamber identifier
    STEP        varchar(20)  NULL,                      -- Process step name or code
    GLASSID     varchar(20)  NULL,                      -- Primary glass/substrate ID
    GLASSID2    varchar(20)  NULL,                      -- Secondary glass/substrate ID
    LOTID       varchar(20)  NULL,                      -- Production lot ID
    HOSTPPID    varchar(20)  NULL,                      -- Host recipe / process program ID
    EQPPPID     varchar(20)  NULL,                      -- Equipment recipe / process program ID
    ACTION      varchar(5)   NOT NULL,                  -- Warning action code (exact code set should be confirmed)
    ALARMID     varchar(6)   NOT NULL,                  -- Warning/alarm identifier code
    ALARMTEXT   varchar(100) NULL,                      -- Warning message text
    FILENAME    varchar(64)  NULL,                      -- Source file name or ingest file name
    CREATETIME  datetime2(7) NULL DEFAULT getdate(),    -- Row creation / insert timestamp

    CONSTRAINT WARNING_LOG_DATA_PK PRIMARY KEY (
        EQPID,
        MODULEID,
        EVENTTIME,
        UNIT,
        ACTION,
        ALARMID
    )
);

-- Recommended semantic notes for retrieval:
-- 1) EVENTTIME is usually the main time filter column for event-range questions.
-- 2) CREATETIME is the record creation time, not necessarily the event occurrence time.
-- 3) ACTION and ALARMID together are key dimensions for grouping or deduplication.


