library(shiny)
library(bslib)
library(shinychat)
library(ellmer)
library(httr2)
library(jsonlite)

source("mcp_client.R")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MCP_URL <- "https://pct.demo.soleng.posit.it/ovintiv/mcp"
MCP_AUTH <- paste("Key", Sys.getenv("CONNECT_API_KEY", "uF9CtvVAKFkPhNSSUgdvXuNtsbmd4AKD"))

# LLM model — override with LLM_MODEL env var if desired
LLM_MODEL <- Sys.getenv("LLM_MODEL", "claude-sonnet-4-6")

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT <- "
You are an expert oil and gas exploration assistant for Ovintiv, with live
access to well data for major North American unconventional plays
through MCP tools.

PLAYS IN THE DATASET
--------------------
- Montney       — Montney West, NE British Columbia, Canada
                  Unconventional gas / condensate
- Duvernay      — Duvernay Central, Central Alberta, Canada
                  Unconventional oil / liquids-rich gas
- Wolfcamp A    — Permian Delaware Basin, West Texas, USA
                  Unconventional oil
- STACK/Meramec — Anadarko Basin, Central Oklahoma, USA
                  Unconventional oil / wet gas

AVAILABLE MCP TOOLS
-------------------
- list_wells           : Inventory with optional filters (formation, status, field)
- get_well_details     : Full technical record for a single well (OVV-XXX-NNN)
- get_production_history: Monthly oil / gas / water with BOE/d and cumulative volumes
- get_field_summary    : Field-level aggregates — well counts, BOE/d, cumulatives
- search_wells         : Multi-criteria filter (lateral length, BOE/d range, etc.)
- get_completion_data  : Frac stages, proppant, fluid, cluster spacing
- get_type_curve       : P10 / P50 / P90 type curves and EUR by formation
- get_economics        : NPV10, IRR, payout period per well or play
- get_drilling_activity: Recent spuds, DUCs, and planned future wells
- compare_wells        : Side-by-side two-well comparison with deltas

BEHAVIOUR GUIDELINES
--------------------
- Always call the appropriate MCP tool(s) to fetch live data; never guess values.
- Use tables (markdown) when presenting lists of wells or multi-column metrics.
- Quote specific well IDs (e.g. OVV-WCA-001) when discussing individual wells.
- If a user asks about a well by partial name or location, use list_wells or
  search_wells first to find the correct well ID before fetching details.
- All data is synthetic and for demonstration purposes only.
"

GREETING <- paste0(
  "## Welcome to the Oil & Gas Explorer\n\n",
  "I have live access to synthetic well data across four unconventional plays: ",
  "**Montney**, **Duvernay**, **Wolfcamp A**, and **STACK/Meramec**.\n\n",
  "I can help you explore well inventory, production histories, completion designs, ",
  "type curves, economics, and drilling activity. What would you like to know?"
)

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

ui <- page_sidebar(
  title = "O&G Explorer",
  theme = bs_theme(
    bootswatch = "flatly",
    primary    = "#003087"
  ),
  fillable   = TRUE,

  sidebar = sidebar(
    width = 300,
    open  = TRUE,

    # ---- Plays card --------------------------------------------------------
    card(
      class = "mb-3",
      card_header("Plays"),
      card_body(
        padding = "0.75rem",
        tags$table(
          class = "table table-sm table-borderless small mb-0",
          tags$tbody(
            tags$tr(
              tags$td(tags$span(class = "badge text-bg-primary", "MNT")),
              tags$td("Montney — BC Canada")
            ),
            tags$tr(
              tags$td(tags$span(class = "badge text-bg-success", "DVN")),
              tags$td("Duvernay — AB Canada")
            ),
            tags$tr(
              tags$td(tags$span(class = "badge text-bg-warning text-dark", "WCA")),
              tags$td("Wolfcamp A — TX USA")
            ),
            tags$tr(
              tags$td(tags$span(class = "badge text-bg-danger", "STK")),
              tags$td("STACK/Meramec — OK USA")
            )
          )
        )
      )
    ),

    # ---- Example questions card -------------------------------------------
    card(
      class = "mb-3",
      card_header("Example questions"),
      card_body(
        padding = "0.75rem",
        tags$ul(
          class = "list-unstyled small mb-0",
          tags$li(
            class = "mb-2",
            actionLink("ex1", "List all active Wolfcamp wells")
          ),
          tags$li(
            class = "mb-2",
            actionLink("ex2", "Compare Montney and Duvernay type curves")
          ),
          tags$li(
            class = "mb-2",
            actionLink("ex3", "Which wells have the highest NPV10?")
          ),
          tags$li(
            class = "mb-2",
            actionLink("ex4", "Show DUCs and planned wells")
          ),
          tags$li(
            class = "mb-2",
            actionLink("ex5", "Production history for OVV-WCA-001")
          )
        )
      )
    ),

    # ---- Status card -------------------------------------------------------
    card(
      card_header("Connection"),
      card_body(
        padding = "0.75rem",
        tags$p(
          class = "small mb-1",
          tags$strong("MCP server:"),
          tags$br(),
          tags$span(
            class = "text-muted font-monospace",
            style = "font-size: 0.75rem; word-break: break-all;",
            MCP_URL
          )
        ),
        tags$p(
          class = "small mb-0",
          tags$strong("Model:"), " ", LLM_MODEL
        )
      )
    )
  ),

  # ---- Main chat panel -----------------------------------------------------
  chat_mod_ui("chat", fill = TRUE)
)

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

server <- function(input, output, session) {

  # Create ellmer chat object — picks up ANTHROPIC_API_KEY automatically.
  chat <- chat_claude(
    system_prompt = SYSTEM_PROMPT,
    model         = LLM_MODEL,
    echo          = "none"
  )

  # Fetch all tools from the FastMCP server and register with the chat object.
  # Uses our custom MCP client (mcp_client.R) which correctly handles
  # Optional[str] parameter schemas that trip up the mcptools package.
  chat$set_tools(make_mcp_tools(MCP_URL, auth = MCP_AUTH))

  # Wire the chat module: handles input, streaming, and tool calls.
  chat_mod_server("chat", client = chat, greeting = GREETING)

  # ---- Example question shortcuts -----------------------------------------
  example_questions <- list(
    ex1 = "List all active Wolfcamp A wells with their current BOE/d rates.",
    ex2 = "Compare the Montney and Duvernay type curves — show P10/P50/P90 IP30 rates, EUR, and average CAPEX for each.",
    ex3 = "Get the economics for all producing wells and rank them by NPV10.",
    ex4 = "Show me all drilled-uncompleted (DUC) wells and planned future wells across all plays.",
    ex5 = "Show the full monthly production history for well OVV-WCA-001."
  )

  purrr::walk(names(example_questions), function(btn_id) {
    observeEvent(input[[btn_id]], {
      update_chat_user_input("chat", value = example_questions[[btn_id]], submit = TRUE)
    })
  })
}

# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------

shinyApp(ui, server)
