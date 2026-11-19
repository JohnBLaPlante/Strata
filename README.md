# Ovintiv O&G Explorer — FastMCP Server

A demonstration **MCP (Model Context Protocol) server** built with [FastMCP](https://github.com/jlowin/fastmcp),
deployable to **Posit Connect**, and connectable from **Claude Code** on the desktop.

The server exposes synthetic oil and gas exploration data covering Ovintiv's major
North American unconventional plays:

| Field | Formation | Region |
|---|---|---|
| Montney West | Montney | NE British Columbia, Canada |
| Duvernay Central | Duvernay | Central Alberta, Canada |
| Permian Delaware Basin | Wolfcamp A | West Texas, USA |
| Anadarko Basin | STACK/Meramec | Central Oklahoma, USA |

> **All data is synthetic.** Generated with a fixed random seed for reproducibility.
> No real production, financial, or location data is used.

---

## Available MCP Tools

| Tool | Description |
|---|---|
| `list_wells` | List all wells; filter by formation, status, or field |
| `get_well_details` | Full details for a single well by ID |
| `get_production_history` | Monthly oil/gas/water production for a well |
| `get_field_summary` | Aggregate stats per field (BOE/d, well counts, cumulatives) |
| `search_wells` | Filter wells by formation, status, lateral length, or BOE/d rate |
| `get_completion_data` | Hydraulic fracture completion design (stages, proppant, fluid) |
| `get_type_curve` | P10/P50/P90 type curve parameters by formation |
| `get_economics` | NPV10, IRR, payout period for a well or entire play |
| `get_drilling_activity` | Recent spuds, DUCs, and planned wells |
| `compare_wells` | Side-by-side comparison of any two wells |

---

## Local Development

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the server

```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Or using the FastMCP runner:

```bash
python server.py
```

The MCP endpoint will be available at:

```
http://localhost:8000/mcp
```

### 3. Test with MCP Inspector (optional)

```bash
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

---

## Deployment to Posit Connect

### Prerequisites

```bash
pip install rsconnect-python
rsconnect add --server https://your-connect-server.com --api-key YOUR_API_KEY --name myconnect
```

### Deploy

```bash
rsconnect deploy fastapi \
  --server myconnect \
  --name ovintiv-oilgas-mcp \
  --title "Ovintiv O&G Explorer MCP" \
  server.py
```

After deployment, note your content URL — it will look like:

```
https://your-connect-server.com/content/<content-id>/
```

The MCP endpoint will be at:

```
https://your-connect-server.com/content/<content-id>/mcp
```

### Content Access Settings

By default, Posit Connect content requires authentication. You can either:

- **Keep auth enabled** (recommended): Users provide a Connect API key as a header.
- **Set to public**: No authentication required — simplest for demos.

To retrieve your Connect API key: go to **Connect → Account → API Keys → New API Key**.

---

## Connecting from Claude Code

Add the following to your Claude Code MCP configuration.

**Location of config file:**
- macOS / Linux: `~/.claude/settings.json`
- Windows: `%APPDATA%\Claude\settings.json`

### With authentication (recommended)

```json
{
  "mcpServers": {
    "ovintiv-oilgas": {
      "type": "http",
      "url": "https://your-connect-server.com/content/<content-id>/mcp",
      "headers": {
        "Authorization": "Key YOUR_CONNECT_API_KEY"
      }
    }
  }
}
```

### Public content (no auth)

```json
{
  "mcpServers": {
    "ovintiv-oilgas": {
      "type": "http",
      "url": "https://your-connect-server.com/content/<content-id>/mcp"
    }
  }
}
```

After saving the config, restart Claude Code. You should see
**ovintiv-oilgas** listed under available MCP servers.

---

## Example Claude Code Prompts

Once connected, try asking Claude Code:

- *"List all active wells in the Montney formation."*
- *"What is the production history for well OVV-WCA-001?"*
- *"Compare the economics of the best Permian well vs. the best Duvernay well."*
- *"Which formation has the highest average NPV10?"*
- *"Show me all DUCs and planned wells across all fields."*
- *"What is the P50 type curve for the Wolfcamp A?"*

---

## Project Structure

```
ovintiv/
├── server.py          # FastMCP server (all tools + synthetic data)
├── requirements.txt   # Python dependencies
├── pyproject.toml     # Project metadata
└── README.md          # This file
```
