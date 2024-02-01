

# load libraries -------------------

library(data.table)
library(stringr)

# reading input data ------------------------------

# THIS IS THE OLD TABLE
# AND NEEDS TO BE UPDATED
df = "Updatedtools.tsv" |> fread()

# Column to exclude ----------------

df$`Galaxy tool ids` = NULL
df$Description       = NULL

df$`bio.tool id`          = NULL
df$`bio.tool name`        = NULL
df$`bio.tool description` = NULL    

df$Source            = NULL

df$`Conda id`      = NULL
df$`Conda version` = NULL

df$`Galaxy wrapper owner`   = NULL
df$`Galaxy wrapper source`  = NULL
df$`Galaxy wrapper version` = NULL

df$`https://usegalaxy.eu`     = NULL
df$`https://usegalaxy.org`    = NULL
df$`https://usegalaxy.org.au` = NULL



# EDAM topic plot ----------------------

df2 = df |>
    tidyr::separate_rows("EDAM topic", sep = ",") |>
    setDT()

df2$`EDAM topic` = df2$`EDAM topic` |> str_squish()

df2 = df2[which(`EDAM topic` != "")]

st = df2[, by = `EDAM topic`, .N]
st = st[order(-N)]
st = st[seq_len(11)]

df2$cluster = ifelse(
    df2$`EDAM topic` %in% st$`EDAM topic`,
    df2$`EDAM topic`, "Other topics"
)

df2 = df2[, c(
    "Galaxy wrapper id", 
    "Total tool usage (usegalaxy.eu)", 
    "No. of tool users (2022-2023) (usegalaxy.eu)", 
    "cluster"
)] |> unique()

df2 = df2[, by = cluster, N := `Galaxy wrapper id` |> unique() |> length()]

df2$cluster = df2$cluster |> factor(levels = c(st$`EDAM topic`, "Other topics"))

df2 = df2[order(cluster)]

df2$strip = paste0("**", df2$cluster, "** (", df2$N, " tools)")
df2$strip = df2$strip |> factor(levels = df2$strip |> unique())

# make the plot ----------------------------------------

library(ggplot2)
library(ggdensity)
library(ggtext)
library(colorspace)
library(extrafont)

gr = ggplot(df2, aes(`Total tool usage (usegalaxy.eu)`, `No. of tool users (2022-2023) (usegalaxy.eu)`)) +
    
    geom_hdr_lines(linewidth = .55, color = darken("#2F509E", .25)) +
    
    geom_point(shape = 21, size = 2, stroke = .2, color = "grey96", fill = "#2E2A2B") +
    
    scale_x_continuous(
        trans = "log10",  expand = c(0, 0), 
        breaks = scales::trans_breaks("log10", function(x) 10^x),
        labels = scales::trans_format("log10", scales::math_format(10^.x))
    ) +
    
    scale_y_continuous(trans = "log10", labels = scales::comma, expand = c(0, 0), breaks = c(1, 10, 100, 1000, 10000)) +
    
    guides(
        alpha = guide_legend(
            title = "Perc. of observations (tools)",
            title.position = "top", 
            title.theme = element_text(family = "Calibri")
        )
    ) +
    
    facet_wrap(vars(strip), nrow = 4) +
    
    coord_equal() +
    
    theme_minimal(base_family = "Calibri") +
    
    theme(
        legend.position = "bottom",
        legend.justification = "left",
        
        strip.text = element_markdown(),
        
        axis.title.x = element_markdown(margin = margin(t = 10)),
        axis.title.y = element_markdown(margin = margin(r = 10)),
        
        axis.ticks = element_line(linewidth = .3),
        
        panel.grid.minor = element_blank(),
        panel.grid.major = element_line(linewidth = .3, linetype = "dashed", color = "grey75"),
        
        panel.border = element_rect(linewidth = .3, fill = NA),
        
        plot.margin = margin(20, 20, 20, 20)
    ) +
    
    labs(
        x = "**Total tool usage** (usegalaxy.eu)",
        y = "**No. of tool users 2022-2023** (usegalaxy.eu)"
    )
    

ggsave(
    plot = gr, filename = "Rplot_topics.png",
    width = 10, height = 12, units = "in", dpi = 600
)    

