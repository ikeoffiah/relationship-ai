from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0001_initial"),
        ("memory", "0001_initial"),
    ]

    def apply_rls(apps, schema_editor):
        if schema_editor.connection.vendor != 'postgresql':
            return
        
        # User Memories RLS
        schema_editor.execute("ALTER TABLE user_memories ENABLE ROW LEVEL SECURITY;")
        schema_editor.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'user_memories_isolation') THEN
                    CREATE POLICY user_memories_isolation ON user_memories
                    USING (user_id = current_setting('app.current_user_id', true)::UUID);
                END IF;
            END $$;
        """)

        # Audit Events RLS
        schema_editor.execute("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;")
        schema_editor.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'audit_insert_only') THEN
                    CREATE POLICY audit_insert_only ON audit_events
                    FOR INSERT WITH CHECK (true);
                END IF;
            END $$;
        """)

        # Memory Vectors RLS & Index
        schema_editor.execute("ALTER TABLE memory_vectors ENABLE ROW LEVEL SECURITY;")
        schema_editor.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'memory_vectors_isolation') THEN
                    CREATE POLICY memory_vectors_isolation ON memory_vectors
                    USING (user_id = current_setting('app.current_user_id', true)::UUID);
                END IF;
            END $$;
        """)
        schema_editor.execute("CREATE INDEX IF NOT EXISTS memory_vectors_hnsw_idx ON memory_vectors USING hnsw (embedding vector_cosine_ops);")

    def remove_rls(apps, schema_editor):
        if schema_editor.connection.vendor != 'postgresql':
            return
            
        schema_editor.execute("DROP INDEX IF EXISTS memory_vectors_hnsw_idx;")
        schema_editor.execute("DROP POLICY IF EXISTS memory_vectors_isolation ON memory_vectors;")
        schema_editor.execute("ALTER TABLE memory_vectors DISABLE ROW LEVEL SECURITY;")
        schema_editor.execute("DROP POLICY IF EXISTS audit_insert_only ON audit_events;")
        schema_editor.execute("ALTER TABLE audit_events DISABLE ROW LEVEL SECURITY;")
        schema_editor.execute("DROP POLICY IF EXISTS user_memories_isolation ON user_memories;")
        schema_editor.execute("ALTER TABLE user_memories DISABLE ROW LEVEL SECURITY;")

    operations = [
        migrations.RunPython(apply_rls, remove_rls),
    ]
