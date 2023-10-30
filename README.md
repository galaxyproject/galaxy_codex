Galaxy Tool extractor
=====================

# What is the tool doing?

- Parse tool GitHub repository from [Planemo monitor listed](https://github.com/galaxyproject/planemo-monitor)
- Check in each repo, their `.shed.yaml` file and filter for metagenomics or other tag
- Extract metadata from the `.shed.yaml`
- Extract the requirements in the macros or xml to get version supported in Galaxy
- Check against conda the available version
- Extract bio.tools information if available in the macros or xml

# Usage

## Prepare environment (virtualenv)

- Install virtualenv (if not already there)

    ```bash
    $ python3 -m pip install --user virtualenv
    ```

- Create virtual environment

    ```bash
    $ python3 -m venv env
    ```

- Activate virtual environment

    ```bash
    $ source env/bin/activate
    ```

- Install requirements

    ```bash
    $ python3 -m pip install -r requirements.txt
    ```

## Prepare environment (conda/mamba)

    ```bash
    $ mamba create -n galaxy_tool_extractor --file requirements.txt
    ```

## Extract all tools

1. Get an API key ([personal token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)) for GitHub
2. Export the GitHub API key as an environment variable:

    ```bash
    $ export GITHUB_API_KEY=<your GitHub API key>
    ```

3. Run the script

    ```bash
    $ python bin/extract_all_tools.sh
    ```

The script will generate a TSV file with each tool found in the list of GitHub repositories and metadata for these tools:

1. Galaxy wrapper id
2. Description
3. bio.tool id
4. bio.tool name
5. bio.tool description
6. EDAM operation
7. EDAM topic
8. Status
9. Source
10. ToolShed categories
11. ToolShed id
12. Galaxy wrapper owner
13. Galaxy wrapper source
14. Galaxy wrapper version
15. Conda id
16. Conda version

## Add tool usage statistics of galaxy instance to the tool list

1. The actual usage statistics need to be queried from the DB of the galaxy instance using a SQL query like:

```sql
select tool_name, count(*) as count from (select distinct regexp_replace(tool_id, '(.*)/(.*)', '\1') as tool_name, user_id from job where create_time >= '2022-01-01 00:00:00.000000' group by tool_name, user_id) as subquery group by tool_name order by count desc;
```

Any Galaxy admin can query this data.

5. Run the add tool stats bash script

```
$ bash bin/add_tool_stats.sh
```

## Filter tools based on their categories in the ToolShed

1. Run the extraction as explained before
2. (Optional) Create a text file with ToolShed categories for which tools need to be extracted: 1 ToolShed category per row ([example for microbial data analysis](data/microgalaxy/categories))
3. (Optional) Create a text file with list of tools to exclude: 1 tool id per row ([example for microbial data analysis](data/microgalaxy/tools_to_exclude))
4. (Optional) Create a text file with list of tools to really keep (already reviewed): 1 tool id per row ([example for microbial data analysis](data/microgalaxy/tools_to_keep))
5. Run the tool extractor script

    ```bash
    $ python bin/extract_galaxy_tools.py \
        --tools <Path to CSV file with all extracted tools> \
        --filtered_tools <Path to output CSV file with filtered tools> \
        [--categories <Path to ToolShed category file>] \
        [--excluded <Path to excluded tool file category file>]\
        [--keep <Path to to-keep tool file category file>]
    ```

### Filter tools for microbial data analysis

For microGalaxy, a Bash script in `bin` can used by running the script

```bash
$ bash bin/extract_microgalaxy_tools.sh
```

It will take the files in the `data/microgalaxy` folder and export the tools into `microgalaxy_tools.csv`
