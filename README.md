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