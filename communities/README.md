**For general and technical information on the Codex, please, refer to the [main Readme file](https://github.com/galaxyproject/galaxy_codex)**


Galaxy Community Codex
============

# Join the CoDex
Any Galaxy Community can be added to this project and benefit from the dedicated resources.

Learn [how to add your community](https://training.galaxyproject.org/training-material/learning-pathways/sig-and-codex-creation.html) in the dedicated GTN learning pathway.

## 1. Galaxy Community Catalog
To generate interactive tables that can be embedded into subdomains and websites via an iframe, follow tutorials 1, 2 and 3 of the [learning pathway](https://training.galaxyproject.org/training-material/learning-pathways/sig-and-codex-creation.html). 

## 2. Galaxy Lab
To generate Galaxy Lab content, you can follow tutorial 4 of the [learning pathway](https://training.galaxyproject.org/training-material/learning-pathways/sig-and-codex-creation.html) and follow [The Galaxy Labs Engine documentation](https://labs.usegalaxy.org.au/).


# Folder organisation

There is a folder `all` with all the tools, workflows, and tutorials extracted weekly from public databases.

Then, each community have their own folder, with a specific organization, with community-specific resources necessary for generating the codex (catalogs and labs). To learn how to create a codex for your community, follow the steps explained in the Learning Pathway available above.

# Galaxy Community Catalog content

## Tool table

The list of tools included in the tool table contains tools from selected ToolShed categories, automatically pulled from the [Galaxy ToolShed](https://galaxyproject.org/toolshed/) on a weekly basis. 

Column | Description
--- | ---
Suite ID | ID of Galaxy suite
Tool IDs | List of Galaxy tool IDs
Description | Description of the suite
Suite first commit date |  | 
Homepage | Homepage for tool
Suite version | Version of the Galaxy suite
Suite Conda package | Conda package used as requirement for the suite 
Latest suite conda package version | Latest Conda package version on anaconda
Suite version status | Update status derived by comparing the suite version to the latest conda package version
ToolShed categories | 
EDAM operations | EDAM operations extracted using bio.tools
EDAM reduced operations | EDAM operations where only the most specific terms are kept, i.e. all terms that are superclasses of other terms are removed
EDAM topics | EDAM topics extracted using bio.tools
EDAM reduced topics | EDAM topics where only the most specific terms are kept, i.e. all terms that are superclasses of other terms are removed
Suite owner | Owner of the Galaxy suite
Suite source | Path to the Galaxy suite
Suite parsed folder | 
bio.tools ID | ID of the bio.tools entry corresponding to the tool
bio.tools name | Name of the bio.tools entry corresponding to the tool
bio.tools description | Description in bio.tools entry corresponding to the tool
bii ID | ID of BII entry corresponding to the tool
Number of tools on ...  | Number of tools available on given Galaxy server
Suite users (last 5 years) on ...  | Number of users of the suite in the last 5 years on given Galaxy server
Suite users on ...  | Number of users of the suite on given Galaxy server
Suite runs (last 5 years) on ...  |  Number of runs of the suite tools in the last 5 years on given Galaxy server
Suite runs on ...  | Number of runs of the suite tools on given Galaxy server
Suite users (last 5 years) on main servers  |  Number of users of the suite in the last 5 years on all UseGalaxy servers
Suite users on main servers  | Number of users of the suite on all UseGalaxy servers
Suite runs (last 5 years) on main servers  | Number of runs of the suite tools in the last 5 years on all UseGalaxy servers
Suite runs on main servers  | Number of runs of the suite tools on all UseGalaxy servers
Deprecated | Deprecation status after review by a domain expert
Related Workflows | Workflows that use at least one tool of the suite
Related Tutorials | Tutorials that use at least one tool of the suite
To keep | Status to add to a tool after review by a domain expert (True / False)
Deprecated | Status to add to a tool after review by a domain expert (True / False)

# Tutorial table

The list of tutorials included in the tutorial table contains tutorials with selected tags, automatically pulled from the [Galaxy Training Network](https://training.galaxyproject.org/) on a weekly basis. 

Column | Description
--- | ---
Topic | Topic associated to the tutorial
Title | Title of the tutorial
Link | Link to the Tutorial on the GTN
EDAM topic | EDAM topics extracted
EDAM operation | EDAM operations extracted
Creation | Date of creation
Last modification | Date of last modification
Version | Version of the tutorial
Tutorial | Does this tutorial includes a tutorial? (True / False)
Slides | Does this tutorial includes slides? (True / False)
Video | Does this tutorial includes a video? (True / False)
Workflows | Does this tutorial includes a workflow? (True / False)
Tools | List of tools included in the tutorial
Servers with precise tool versions | List of Galaxy servers with tools available with the version specified in the tutorial
Servers with tool but different versions | List of Galaxy servers with tools available in a different version from the one specified in the tutorial
Feedback number | Number of feedback
Feedback mean note | Mean note of the tutorial
Visitors | Number of visitors
Page views | Number of page views
Visit duration | Mean visit duration 
Video views | Number of times the video was viewed

# Workflow table

The list of workflows included in the workflow table contains workflows with specific tags, automatically pulled from the public Galaxy instances and [WorkflowHub](https://workflowhub.eu/) on a weekly basis. 

Column | Description
--- | ---
Name | Workflow name
Source | Workflow source (i.e. WorkflowHub, galaxy instance name, etc)
ID | Workflow unique ID
Link | Link to the workflow
Creators | Creator full names (when available)
Tags | Tags associated to the workflow
Creation time | Date of workflow creation
Update time | Date of the last update to the workflow
Latest version | Latest version
Versions | Number of versions
Number of steps | 
Tools | List of tools used by the workflow
EDAM operations | 
EDAM topics | 
License | 
DOI | 
Projects | 
To keep | Status to add to a workflow after review by a domain expert (True / False)
Deprecated | Status to add to a workflow after review by a domain expert (True / False)
