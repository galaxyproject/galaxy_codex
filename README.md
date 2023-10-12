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

## Prepare environment

- Install virtualenv (if not already there)

    ```
    $ python3 -m pip install --user virtualenv
    ```

- Create virtual environment

    ```
    $ python3 -m venv env
    ```

- Activate virtual environment

    ```
    $ source env/bin/activate
    ```

- Install requirements

    ```
    $ python3 -m pip install -r requirements.txt
    ```

# Extract tools for categories in the ToolShed

1. Get an API key ([personal token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)) for GitHub
2. (Optional) Create a text file with ToolShed categories for which tools need to be extracted: 1 ToolShed category per row
3. (Optional) Create a text file with list of tools to exclude: 1 tool id per row
4. Run the tool extractor script

    ```
    $ python bin/extract_galaxy_tools.py \
        --api <GitHub API key> \
        --output <Path to output file> \
        [--categories <Path to ToolShed category file>] \
        [--excluded <Path to excluded tool file category file>]
    ```