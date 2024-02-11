---
title: 'How to increase the findability, visibility, and impact of Galaxy tools for your scientific community'
title_short: 'BioHackEU23 project #25: Finding Galaxy tools'
tags:
  - Findability
  - Galaxy
  - Community specific
authors:
  - name: Paul Zierep*
	orcid:
	affiliation: 1
  - name: Berenice Batut
	orcid:
	affiliation: 2
  - name: Nicola Soranzo
	orcid: 0000-0003-3627-5340
	affiliation: 3
  - name: Matúš Kalaš
	orcid:
	affiliation: 4
  - name: Ove Johan Ragnar Gustafsson
	orcid: 0000-0002-2977-5032
	affiliation: 5
affiliations:
  - name: 
	index: 1
  - name: 
	index: 2
  - name: Earlham Institute, Norwich Research Park, Norwich, UK
	index: 3
  - name: 
	index: 4
  - name: Australian BioCommons, University of Melbourne, Melbourne, Victoria, Australia
	index: 5
date: 12 February 2024
bibliography: paper.bib
event: BioHackathon Europe 2023
biohackathon_name: "BioHackathon Europe 2023"
biohackathon_url:   "https://biohackathon-europe.org/"
biohackathon_location: "Barcelona, Spain, 2023"
group: BioHackrXiv
git_url: https://github.com/galaxyproject/galaxy_tool_metadata_extractor/tree/e604ffd9866f9c32f797ceee45062b4d6f2a1513/docs/publications/BioHackrXiv
authors_short: Zierep, P., Batut, B. \emph{et al.} (2024) BioHackEU23 project #25: Finding Galaxy tools


---

# Introduction or Background

Galaxy[@10.1093/nar/gkac247] offers almost 10,000 tools that are developed across different Git repositories. Furthermore, Galaxy also embraces granular implementation of software tools as sub-modules. In practice, this means that tool suites are separated into Galaxy tools, also known as wrappers, that capture their component operations. Some key examples of suites include [Mothur](https://bio.tools/mothur)[@doi:10.1128/AEM.01541-09] and [OpenMS](https://bio.tools/openms)[@rost2016openms], which translate to tens and even hundreds of Galaxy tools. While granularity supports the sustainable development of rich domain-specific workflows, the reality is that this decentralized development and sub-module architecture makes it difficult for Galaxy users to find and reuse tools. It may also result in Galaxy developers replicating efforts by simultaneously wrapping new tools. This is further complicated by a lack of tool metadata, which prevents filtering for all tools in a specific research community or domain, and makes it all but impossible to employ advanced filtering with ontology terms and operations like EDAM[@black2021edam]. The final challenge is also an opportunity: the global nature of Galaxy means that it is a big community. Solving the visibility of tools across this ecosystem and the potential benefits are far-reaching for global collaboration on tool and workflow development.


To provide the research community with a comprehensive list of available Galaxy tools, a pipeline was developed at the ELIXIR BioHackathon Europe 2023 that collects Galaxy wrappers from a list of Git repositories and automatically extracts their metadata (including Conda version, bio.tools[@ison2016tools] identifiers, and EDAM annotations). The workflow also queries the availability of the tools and usage statistics from the three main Galaxy servers (usegalaxy.*). 


Crucially, the pipeline can filter its inputs to only include tools that are relevant to a specific research community. Based on the selected filters, a community-specific interactive table is generated that can be embedded, e.g. into the respective Galaxy Hub page or Galaxy subdomain. This table allows further filtering and searching for fine-grained tool selection. The pipeline is fully automated and executes on a weekly basis. Any research community can apply the pipeline to create a table specific to their community.


An interactive table that presents metadata is only as useful as the metadata annotations it is capturing. To improve the metadata coverage for the interactive table, the project also directly addressed the quality of tool annotations in bio.tools for the microGalaxy community: a community with a focus on tools related to microbial research. Annotation guidelines were established for this purpose, the process of updating Galaxy tool wrappers to include bio.tools identifiers was started and the outcome of these activities was evaluated using a crowdsourced approach. During the BioHackathon Europe week, the annotation practices were applied to the tools selected from the microGalaxy community. This effort allowed the team to connect more than 50 tools to their respective bio.tools entry, update the registry entry, and peer-review the result. 


The established pipeline and the annotation guidelines can support any research community to improve the findability, visibility, comparability, and accessibility of their Galaxy tools. Here we describe the methods and processes that resulted from this project and highlight how this will now allow the microGalaxy community to confidently navigate an ever-expanding landscape of research software in the Galaxy framework. 


## Subsection level 2

Please keep sections to a maximum of three levels, even better if only two levels.

### Subsection level 3

Please keep sections to a maximum of three levels.

## Tables, figures and so on

Please remember to introduce tables (see Table 1) before they appear on the document. We recommend to center tables, formulas and figure but not the corresponding captions. Feel free to modify the table style as it better suits to your data.

Table 1
| Header 1 | Header 2 |
| -------- | -------- |
| item 1 | item 2 |
| item 3 | item 4 |

Remember to introduce figures (see Figure 1) before they appear on the document. 

![BioHackrXiv logo](./biohackrxiv.png)
 
Figure 1. A figure corresponding to the logo of our BioHackrXiv preprint.



# Methods

## Domain-specific interactive tools table

Galaxy tool wrapper suites are first parsed from multiple GitHub repositories. In effect, the repositories monitored by the planemo-monitor [@Bray2022.03.13.483965] are scraped using a custom script. The planemo-monitor is part of the Galaxy tool update infrastructure and keeps track of the most up-to-date tool development repositories. 
Metadata is extracted from each tool wrapper suite. This includes: wrapper suite ID, scientific category, BioConda dependency, and a bio.tools repository URL. As a tool suite can be composed of multiple individual tools, the tool IDs for each tool are also extracted.
The bio.tools reference is used to request annotations via the bio.tools API, including bio.tools description, EDAM function, and EDAM operation[@black2021edam]. The conda package version is retrieved via the BioConda API and compared to the tool wrapper API to determine a tool’s update state (i.e. to update, no update required). 
The Galaxy API is used to query if each tool is installed on one of the three large Galaxy servers ([usegalaxy.eu](https://usegalaxy.eu/), [usegalaxy.org](https://usegalaxy.org/), [usegalaxy.org.au](https://usegalaxy.org.au/)). Furthermore, the tool usage statistics can be retrieved from an SQL query that needs to be executed by Galaxy admins. The query used in the current implementation shows how many users executed a tool in the last 2 years on the european server ([usegalaxy.eu](https://usegalaxy.eu/)). 
The output of the pipeline is a table that combines Galaxy wrappers with their metadata. The complete table can then be filtered to include only tools with relevance for specific communities. The initial filtering step is based on the scientific category, which is defined for every Galaxy wrapper. These categories are high-level and cannot distinguish between specific tool functions. However, they allow for the isolation of a subgroup of the initial table for further curation. The filtered table can be manually curated by community curators. The curation step involves annotating which of the extracted tools should be kept in the final table. Curators can use the EDAM annotations and tool descriptions to assist with this curation step. The labels for each tool are stored to reduce replication of effort even further. The practical outcome is that for repeat executions of the workflow, only new tools require curation. 
The curated tools are transformed into an interactive web table using the data tables framework (**cite**). The table is hosted on GitHub and deployed via GitHub pages for each community. This implementation enables complex queries and filtering without the need for a database backend. The table can be embedded in any website via an iframe: examples include the Galaxy community Hub page for microGalaxy (**cite**) or a specific Galaxy subdomain (**cite**). Furthermore, a word cloud based on the usage statistics of the tools is created. 
The workflow is scheduled via GitHub actions to run on a weekly basis, providing an up-to-date table for each community. The usage of an iframe enables updates for the table to propagate automatically to any website where it is  deployed. Any Galaxy community can use the pipeline by adding a folder in the [GitHub repository](https://github.com/galaxyproject/galaxy_tool_extractor/data/communities). To initialize the pipeline for a new community you need to add a list of categories to a file called categories. Additionally tools that should be excluded or included after filtering can be added to respective files as well. A working example of the community configuration files can be found in the folder for the microgalaxy community. 

![Workflow of the Galaxy tool metadata extractor pipeline. Tool wrappers are parsed from different repositories and additional metadata is retrieved from bio.tools, BioConda, and the main public Galaxy servers. Upon filtering and manual curation of the data for specific scientific communities, the data is transformed into interactive web tables and a tool usage statistic-base word cloud, that can be integrated into any website. \label{metadata_extractor_pipeline}](./figures/________.png)


## Annotation workflow

The annotation process begins by selecting a tool from a Galaxy community. This step can make use of the interactive table created by the Galaxy tool extractor scripts presented above. A curator then needs to visit the development repository of the Galaxy tool wrapper and check the *.xml file for a bio.tools xref snippet (Figure \ref{xref_snippet}). 

![xref snippet example for a Galaxy tool wrapper that contains the tool [Racon](https://bio.tools/Racon). \label{xref_snippet}](./figures/________.png)

bio.tools is then checked to confirm that a bio.tools identifier does, or does not, exist. The reason for this is that even if a bio.tools identifier exists in a tool wrapper, it may not necessarily exist in bio.tools. This is an observation based on real-world annotation errors and serves as a useful supporting step to improve Galaxy wrapper annotations and the completeness of the bio.tools registry. In addition, if a bio.tools identifier is not included in the wrapper, this does not mean that there is not a bio.tools identifier available in the registry.
There are then two curation paths to choose from, depending on if a bio.tools identifier exists in the XML wrapper. In both cases, if no bio.tools entry exists, a new entry should be created and updated using the bio.tools wizard. The creation and update of an entry includes adding EDAM ontology topics and operations. This annotation process can be simplified through the use of [EDAM browser](https://edamontology.github.io/edam-browser/).


In the case where no bio.tools identifier exists in the Galaxy *.xml wrapper, the development repository needs to be forked and a new branch created. A new xref snippet can then be added, and a pull request (PR) generated against the original repository.
Figure \ref{annotation_workflow} shows a step-by-step breakdown of the above process.
![Step-by-step workflow for systematically improving metadata annotations across bio.tools registry entries and Galaxy tool wrappers. After selecting a Galaxy tool and checking for the presence of a bio.tools ID in its XML file, a curator needs to review bio.tools, create a new bio.tools entry (if needed), and then ensure that both this entry and the Galaxy tool XML file are up-to-date. Updating bio.tools makes use of the registry wizard, and updating a Galaxy tool wrapper to include a bio.tools xref snippet requires a pull request against the development repository. \label{annotation_workflow}](./figures/________.png)


# Discussion and/or Conclusion

We recommend to include some discussion or conclusion about your work. Feel free to modify the section title as it fits better to your manuscript.

# Future work

And maybe you want to add a sentence or two on how you plan to continue. Please keep reading to learn about citations and references.

For citations of references, we prefer the use of parenthesis, last name and year. If you use a citation manager, Elsevier – Harvard or American Psychological Association (APA) will work. If you are referencing web pages, software or so, please do so in the same way. Whenever possible, add authors and year. We have included a couple of citations along this document for you to get the idea. Please remember to always add DOI whenever available, if not possible, please provide alternative URLs. You will end up with an alphabetical order list by authors’ last name.

# Jupyter notebooks, GitHub repositories and data repositories

* Please add a list here
* Make sure you let us know which of these correspond to Jupyter notebooks. Although not supported yet, we plan to add features for them
* And remember, software and data need a license for them to be used by others, no license means no clear rules so nobody could legally use a non-licensed research object, whatever that object is

# Acknowledgements
Please always remember to acknowledge the BioHackathon, CodeFest, VoCamp, Sprint or similar where this work was (partially) developed.

# References

Leave thise section blank, create a paper.bib with all your references.