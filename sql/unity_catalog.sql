-- Provisioning template only: review principals and external-location policy before running.
CREATE CATALOG IF NOT EXISTS IDENTIFIER(:catalog) COMMENT 'Environment-isolated retail lakehouse';
CREATE SCHEMA IF NOT EXISTS IDENTIFIER(:catalog || '.' || :schema) COMMENT 'Managed Delta tables and job Volumes';
CREATE VOLUME IF NOT EXISTS IDENTIFIER(:catalog || '.' || :schema || '.landing') COMMENT 'CSV landing files';
CREATE VOLUME IF NOT EXISTS IDENTIFIER(:catalog || '.' || :schema || '.schema_state') COMMENT 'Auto Loader inferred schema state';
CREATE VOLUME IF NOT EXISTS IDENTIFIER(:catalog || '.' || :schema || '.checkpoints') COMMENT 'Auto Loader checkpoints';
GRANT USE CATALOG ON CATALOG IDENTIFIER(:catalog) TO `retail_engineers`;
GRANT USE SCHEMA, SELECT, MODIFY, CREATE TABLE, READ VOLUME, WRITE VOLUME ON SCHEMA IDENTIFIER(:catalog || '.' || :schema) TO `retail_engineers`;
GRANT USE CATALOG ON CATALOG IDENTIFIER(:catalog) TO `retail_analysts`;
GRANT USE SCHEMA, SELECT ON SCHEMA IDENTIFIER(:catalog || '.' || :schema) TO `retail_analysts`;
