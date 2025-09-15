# SQL command to get those stats

Needs to be run via the Galaxy Admin Stats Account

# tool usage last 5 years
```sql
\copy (SELECT DISTINCT REGEXP_REPLACE(j.tool_id, '(.*)/(.*)', '\1') AS tool_name, COUNT(*) AS count FROM job j WHERE j.create_time BETWEEN '2020-08-31' AND '2025-08-31' GROUP BY tool_name ORDER BY count DESC) TO 'tool_usage_5y_until_2025.08.31.csv' WITH CSV HEADER
```

# tool usage for ever
```sql
\copy (SELECT DISTINCT REGEXP_REPLACE(j.tool_id, '(.*)/(.*)', '\1') AS tool_name, COUNT(*) AS count FROM job j WHERE j.create_time <= '2025-08-31' GROUP BY tool_name ORDER BY count DESC) TO 'tool_usage_until_2025.08.31.csv' WITH CSV HEADER
```

# tool users last 5 years
```sql
\copy (SELECT tool_name, COUNT(*) AS count FROM (SELECT DISTINCT REGEXP_REPLACE(tool_id, '(.*)/(.*)', '\1') AS tool_name, user_id FROM job WHERE create_time BETWEEN '2020-08-31' AND '2025-08-31' GROUP BY tool_name, user_id) AS subquery GROUP BY tool_name ORDER BY count DESC) TO 'tool_users_5y_until_2025.08.31.csv' WITH CSV HEADER
```

# tool users for ever
```sql
\copy (SELECT tool_name, COUNT(*) AS count FROM (SELECT DISTINCT REGEXP_REPLACE(tool_id, '(.*)/(.*)', '\1') AS tool_name, user_id FROM job WHERE create_time <= '2025-08-31' GROUP BY tool_name, user_id) AS subquery GROUP BY tool_name ORDER BY count DESC) TO 'tool_users_until_2025.08.31.csv' WITH CSV HEADER
```