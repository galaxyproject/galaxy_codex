Generate tool stats
===================

To add usage stats for the community tools the tool `generate_tool_stats.py` can be used.

Get the stats
=============

The actual stats need to be queried from the DB of the galaxy instance using the SQL query:

```sql
select tool_name, count(*) as count from (select distinct regexp_replace(tool_id, '(.*)/(.*)', '\1') as tool_name, user_id from job where create_time >= '2022-01-01 00:00:00.000000' group by tool_name, user_id) as subquery group by tool_name order by count desc;
```

Any Galaxy admin can query this data.


Install
=======

Install with conda:

```bash
conda create tstats
conda activate tstats
conda install -f requirements.txt
```

Run
===

```bash
python generate_tool_stats.py -ct data/microGalaxy/microGalaxy_tools_mod.csv -ts data/microGalaxy/tool_usage_per_people_2022.csv -wcm data/microGalaxy/wordcloud_mask.png -o output/microGalaxy
```