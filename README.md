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

# Run

```
$ python bin/...
```

# Proposed improvements for the tool

* Check toolshed if tool is deployed and up-to-date
* Check on galaxy instances if tool is deployed and up-to-date
* Check duplicated tools (maybe increment if already found: tool1, tool2 ...)
* Walk trough complete git repository and check all folders with .shed file
* Improve conda lookup 
    * Only one requirement is checked
    * If the tool has no requirement (only script, set to up-to-date ?)
* How to handle suits ? 

# Proposal for the BH 2023

* Update an already existing csv with the newly loaded data (i.e. keep the added columns)
* Maybe the logic could be changed so that all tools are extracted and then subsequently only the bio.tools annotation is used for filtering
    * That would allow for a nice comparison of bio.tool improvement 
* It would be interesting to see how many of the tools parsed from github are in the toolshed if all then probably 
    * Could the toolshed be used as initial source ?
* Cron job
* Data Table Output
* How to allow community to add comments to tools ? 
