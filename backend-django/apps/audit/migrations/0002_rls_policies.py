from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0001_initial"),
        ("memory", "0001_initial"),
    ]

    operations = [
        # User Memories RLS
        migrations.RunSQL(
            sql="ALTER TABLE user_memories ENABLE ROW LEVEL SECURITY;",
            reverse_sql="ALTER TABLE user_memories DISABLE ROW LEVEL SECURITY;",
        ),
        migrations.RunSQL(
            sql="""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'user_memories_isolation') THEN
                    CREATE POLICY user_memories_isolation ON user_memories
                    USING (user_id = auth.uid());
                END IF;
            END $$;
            """,
            reverse_sql="DROP POLICY IF EXISTS user_memories_isolation ON user_memories;",
        ),
        # Audit Events RLS
        migrations.RunSQL(
            sql="ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;",
            reverse_sql="ALTER TABLE audit_events DISABLE ROW LEVEL SECURITY;",
        ),
        migrations.RunSQL(
            sql="""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'audit_insert_only') THEN
                    CREATE POLICY audit_insert_only ON audit_events
                    FOR INSERT WITH CHECK (true);
                END IF;
            END $$;
            """,
            reverse_sql="DROP POLICY IF EXISTS audit_insert_only ON audit_events;",
        ),
        # Memory Vectors RLS & Index
        migrations.RunSQL(
            sql="ALTER TABLE memory_vectors ENABLE ROW LEVEL SECURITY;",
            reverse_sql="ALTER TABLE memory_vectors DISABLE ROW LEVEL SECURITY;",
        ),
        migrations.RunSQL(
            sql="""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'memory_vectors_isolation') THEN
                    CREATE POLICY memory_vectors_isolation ON memory_vectors
                    USING (user_id = current_setting('app.current_user_id', true)::UUID);
                END IF;
            END $$;
            """,
            reverse_sql="DROP POLICY IF EXISTS memory_vectors_isolation ON memory_vectors;",
        ),
        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS memory_vectors_hnsw_idx ON memory_vectors USING hnsw (embedding vector_cosine_ops);",
            reverse_sql="DROP INDEX IF EXISTS memory_vectors_hnsw_idx;",
        ),
    ]
