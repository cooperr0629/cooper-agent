-- 阶段 2：对话历史
-- 执行：docker compose exec -T db psql -U kb -d kb < migrations/001_init.sql

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- 提供 gen_random_uuid()

CREATE TABLE IF NOT EXISTS conversations (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title          text,
    prompt_version text        NOT NULL DEFAULT 'v1',
    created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id uuid        NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            text        NOT NULL CHECK (role IN ('user', 'assistant')),
    content         text        NOT NULL,
    usage           jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- 按对话取历史时要按时间排序，这个联合索引正好覆盖
CREATE INDEX IF NOT EXISTS idx_messages_conv_created
    ON messages (conversation_id, created_at);
