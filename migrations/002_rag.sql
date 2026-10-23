-- 阶段 3：文档与向量
-- 执行：docker compose exec -T db psql -U kb -d kb < migrations/002_rag.sql

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    filename        text        NOT NULL,
    -- 下面四个字段是为了「归因」：阶段 4 要对比不同切分策略、不同 embedding 模型的效果，
    -- 没有这些字段就分不清库里哪批 chunk 是用什么配置生成的（和 prompt_version 同理）
    strategy        text        NOT NULL,
    chunk_size      int,
    embedding_model text        NOT NULL,
    embedding_dim   int         NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id uuid        NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index int         NOT NULL,
    text        text        NOT NULL,
    heading     text,
    embedding   vector(1024) NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks (document_id);

-- 故意不建 HNSW 索引：阶段 3 第 ④⑤ 步要对比「暴力扫描 vs HNSW」，
-- 现在建了就没得比了。
