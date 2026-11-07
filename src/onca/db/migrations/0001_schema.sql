CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE regions (
    id   smallint PRIMARY KEY,
    name text NOT NULL UNIQUE
);

INSERT INTO regions (id, name) VALUES
    (1, 'Norte'),
    (2, 'Nordeste'),
    (3, 'Sudeste'),
    (4, 'Sul'),
    (5, 'Centro-Oeste');

CREATE TABLE states (
    uf        char(2) PRIMARY KEY,
    name      text NOT NULL UNIQUE,
    name_norm text NOT NULL,
    region_id smallint NOT NULL REFERENCES regions (id)
);

CREATE TABLE municipalities (
    ibge_code integer PRIMARY KEY,
    name      text NOT NULL,
    name_norm text NOT NULL,
    uf        char(2) NOT NULL REFERENCES states (uf)
);

CREATE INDEX municipalities_name_norm_idx ON municipalities (name_norm);
CREATE INDEX municipalities_uf_idx ON municipalities (uf);

CREATE TABLE documents (
    id           bigserial PRIMARY KEY,
    source       text NOT NULL,
    url          text NOT NULL,
    title        text NOT NULL,
    published_at timestamptz,
    kind         text NOT NULL CHECK (kind IN ('guideline', 'news')),
    content_hash text NOT NULL UNIQUE,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX documents_kind_published_idx ON documents (kind, published_at);

CREATE TABLE chunks (
    id          bigserial PRIMARY KEY,
    document_id bigint NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    position    integer NOT NULL DEFAULT 0,
    text        text NOT NULL,
    embedding   vector(384),
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX chunks_document_idx ON chunks (document_id);
CREATE INDEX chunks_embedding_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops);
