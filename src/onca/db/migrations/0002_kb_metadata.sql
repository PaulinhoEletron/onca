ALTER TABLE documents ADD COLUMN metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX documents_url_idx ON documents (url);
