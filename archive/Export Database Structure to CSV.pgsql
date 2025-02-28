COPY (
    SELECT 
        t.table_schema,
        t.table_name,
        c.column_name,
        c.data_type,
        c.character_maximum_length,
        c.column_default,
        c.is_nullable,
        c.udt_name,
        (
            SELECT pg_catalog.col_description(
                format('%s.%s', t.table_schema, t.table_name)::regclass::oid, 
                c.ordinal_position
            )
        ) as column_description,
        (
            SELECT string_agg(tc.constraint_type, ', ')
            FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage ccu 
                ON tc.constraint_name = ccu.constraint_name
                AND tc.table_schema = ccu.table_schema
            WHERE tc.table_schema = t.table_schema
                AND tc.table_name = t.table_name
                AND ccu.column_name = c.column_name
        ) as constraints
    FROM information_schema.tables t
    JOIN information_schema.columns c 
        ON t.table_schema = c.table_schema 
        AND t.table_name = c.table_name
    WHERE t.table_schema NOT IN ('pg_catalog', 'information_schema')
        AND t.table_type = 'BASE TABLE'
    ORDER BY 
        t.table_schema,
        t.table_name,
        c.ordinal_position
) TO '/tmp/database_structure.csv' WITH CSV HEADER; 