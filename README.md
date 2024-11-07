Galaxy Codex
============

Galaxy Communities Dock (Galaxy CoDex) is a catalog of resources for Galaxy communities.

Currently, we have two main resources:

1. **Galaxy Community Catalog**: from tools, training & workflows
2. **Galaxy Labs**: (led by Galaxy Australia!) main and tool panel content for communities to spin up subdomain pages

This repository stores the sources to build all of this content. The catalog is automatically updated every week.

# Join the CoDex
Any Galaxy Community can be added to this project and benefit from the dedicated resources.
**Learn [how to add your community](https://training.galaxyproject.org/training-material/topics/community/faqs/codex.html)** in the dedicated GTN tutorial.

# Galaxy Community Catalog
To generate interactive tables that can be embedded into Galaxy Labs (subdomains) and websites via an iframe. 
**Learn [how to generate the Galaxy Community Catalog](https://training.galaxyproject.org/training-material//topics/dev/tutorials/community-tool-table/tutorial.html)** in the dedicated GTN tutorial. 

# Galaxy Lab
To generate GalaxyLab content, you can follow our documentation (to be added!).
To spin up a GalaxyLab on your server, you can follow our documentation (to be added!).

# Galaxy Community Catalog content

## Tool table

Column | Description
--- | ---
Suite ID | ID of Galaxy suite
Tool IDs | List of Galaxy tool IDs
Description | Description of the suite
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
bio.tools ID | ID of the bio.tools entry corresponding to the tool
bio.tools name | Name of the bio.tools entry corresponding to the tool
bio.tools description | Description in bio.tools entry corresponding to the tool
bii ID | ID of BII entry corresponding to the tool
Number of tools available on ...  | Number of tools available on given Galaxy server
Suite users (last 5 years) on ...  | Number of users of the suite in the last 5 years on given Galaxy server
Suite users on ...  | Number of users of the suite on given Galaxy server
Suite runs (last 5 years) on ...  |  Number of runs of the suite tools in the last 5 years on given Galaxy server
Suite runs on ...  | Number of runs of the suite tools on given Galaxy server
Suite users (last 5 years) on main servers  |  Number of users of the suite in the last 5 years on all UseGalaxy servers
Suite users on main servers  | Number of users of the suite on all UseGalaxy servers
Suite runs (last 5 years) on main servers  | Number of runs of the suite tools in the last 5 years on all UseGalaxy servers
Suite runs on main servers  | Number of runs of the suite tools on all UseGalaxy servers
Deprecated | Deprecation status after review by a domain expert
To keep | Status to add to a community after review by a domain expert

# Vocabulary
**Galaxy Lab**: Formerly known as Subdomains, Galaxy Australia built a new method for generating the main and tool panels for a Galaxy subdomain, known as a Galaxy Lab.
**Galaxy Community**: Galaxy Community of Practice. You can see a full list of Special Interest Groups in the [SIG Directory](https://galaxyproject.org/community/sig).
