# SQL command to get those stats

Needs to be run via the Galaxy Admin Stats Account

# tool usage last 5 years
```sql
\set snapshot_date `date '+%Y-%m-01'`

\copy (
    SELECT 
        DISTINCT REGEXP_REPLACE(j.tool_id, '(.*)/(.*)', '\1') AS tool_name,
        COUNT(*) AS count,
        date_trunc('month', CURRENT_DATE) AS snapshot_date
    FROM job j
    WHERE j.create_time BETWEEN (date_trunc('month', CURRENT_DATE) - INTERVAL '5 years') 
                             AND date_trunc('month', CURRENT_DATE)
    GROUP BY tool_name
    ORDER BY count DESC
) 
TO :'tool_usage_5y_until_' || :'snapshot_date' || '.csv' WITH CSV HEADER;
```

# tool usage for ever
```sql
\set snapshot_date `date '+%Y-%m-01'`

\copy (
    SELECT 
        DISTINCT REGEXP_REPLACE(j.tool_id, '(.*)/(.*)', '\1') AS tool_name,
        COUNT(*) AS count,
        date_trunc('month', CURRENT_DATE) AS snapshot_date
    FROM job j
    WHERE j.create_time <= date_trunc('month', CURRENT_DATE)
    GROUP BY tool_name
    ORDER BY count DESC
) 
TO :'tool_usage_until_' || :'snapshot_date' || '.csv' WITH CSV HEADER;

```

# tool users last 5 years
```sql
\set snapshot_date `date '+%Y-%m-01'`

\copy (
    SELECT 
        tool_name,
        COUNT(*) AS count,
        date_trunc('month', CURRENT_DATE) AS snapshot_date
    FROM (
        SELECT 
            DISTINCT REGEXP_REPLACE(tool_id, '(.*)/(.*)', '\1') AS tool_name,
            user_id
        FROM job
        WHERE create_time BETWEEN (date_trunc('month', CURRENT_DATE) - INTERVAL '5 years') 
                              AND date_trunc('month', CURRENT_DATE)
        GROUP BY tool_name, user_id
    ) AS subquery
    GROUP BY tool_name
    ORDER BY count DESC
) 
TO :'tool_users_5y_until_' || :'snapshot_date' || '.csv' WITH CSV HEADER;

```

# tool users for ever
```sql
\set snapshot_date `date '+%Y-%m-01'`

\copy (
    SELECT 
        tool_name,
        COUNT(*) AS count,
        date_trunc('month', CURRENT_DATE) AS snapshot_date
    FROM (
        SELECT DISTINCT 
            REGEXP_REPLACE(tool_id, '(.*)/(.*)', '\1') AS tool_name,
            user_id
        FROM job
        WHERE create_time <= date_trunc('month', CURRENT_DATE)
        GROUP BY tool_name, user_id
    ) AS subquery
    GROUP BY tool_name
    ORDER BY count DESC
) 
TO :'tool_users_until_' || :'snapshot_date' || '.csv' WITH CSV HEADER;
```