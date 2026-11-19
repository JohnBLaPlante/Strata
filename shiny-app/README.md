# Ovintiv O&G Explorer — Shiny Chat App

A Shiny application that connects to the **Ovintiv O&G Explorer FastMCP server**
on Posit Connect and provides a natural-language chat interface for exploring
synthetic well data.

---

## Architecture

```
User (browser)
    │
    ▼
Shiny App (shinychat + elmer)
    │  natural-language chat
    ▼
LLM (Claude via Anthropic API)
    │  MCP tool calls
    ▼
FastMCP Server (Posit Connect)
    │  /mcp  Streamable HTTP
    ▼
Synthetic O&G dataset (25 wells, 4 plays)
```

---

## Required packages

```r
install.packages(c("shiny", "bslib", "purrr"))

# Posit packages — install from r-universe if not on CRAN
install.packages(
  c("shinychat", "elmer"),
  repos = c("https://posit-dev.r-universe.dev", getOption("repos"))
)
```

---

## Environment variables

| Variable          | Description                              | Required |
|-------------------|------------------------------------------|----------|
| `ANTHROPIC_API_KEY` | Anthropic API key (picked up by elmer automatically) | ✅ |
| `MCP_SERVER_URL`  | Override MCP server URL (defaults to the demo Connect URL) | optional |
| `CONNECT_API_KEY` | Posit Connect API key for the MCP server | optional (default bundled for demo) |
| `LLM_MODEL`       | Claude model name override               | optional |

---

## Running locally

```r
# From the shiny-app/ directory:
shiny::runApp()
```

Or from R:

```r
shiny::runApp("shiny-app/")
```

---

## Deploying to Posit Connect

```r
library(rsconnect)

rsconnect::deployApp(
  appDir     = "shiny-app/",
  appName    = "ovintiv-oilgas-chat",
  appTitle   = "Ovintiv O&G Explorer",
  forceUpdate = TRUE
)
```

Set `ANTHROPIC_API_KEY` in the Connect content's environment variables after deployment:
**Content → Vars tab → Add ANTHROPIC_API_KEY**.

---

## Example questions

- "List all active wells and their current BOE/d rates."
- "What's the production history for OVV-WCA-001?"
- "Compare the Montney and Wolfcamp A type curves."
- "Which formation has the highest average NPV10?"
- "Show me all DUCs and planned wells."
- "Compare OVV-MNT-001 and OVV-DVN-001 side by side."
- "What is the P50 EUR for the Duvernay?"
- "Which Wolfcamp wells are producing above 300 BOE/d?"
