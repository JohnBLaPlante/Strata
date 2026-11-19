# mcp_client.R
# ---------------------------------------------------------------------------
# Minimal MCP Streamable-HTTP client that converts server tools into a list
# of ellmer-compatible tool objects.
#
# Works around a mcptools bug where `anyOf: [{type: string}, {type: null}]`
# schemas (produced by FastMCP for Optional[str] parameters) trigger a
# subscript-out-of-bounds error during schema parsing.
# ---------------------------------------------------------------------------

#' Connect to a Streamable-HTTP MCP server and return ellmer tool objects
#'
#' @param url   Full MCP endpoint URL, e.g. "https://host/path/mcp"
#' @param auth  Value for the Authorization header (or NULL for no auth)
#' @return      Named list of ellmer::tool objects ready for chat$set_tools()
make_mcp_tools <- function(url, auth = NULL) {

  # ---- helpers --------------------------------------------------------------

  # Build a prepared httr2 request with standard MCP headers
  new_req <- function(session_id = NULL) {
    req <- httr2::request(url) |>
      httr2::req_method("POST") |>
      httr2::req_headers(
        "Content-Type" = "application/json",
        "Accept"       = "application/json, text/event-stream"
      )
    if (!is.null(auth))        req <- httr2::req_headers(req, "Authorization" = auth)
    if (!is.null(session_id))  req <- httr2::req_headers(req, "MCP-Session-Id" = session_id)
    req
  }

  jsonrpc <- function(method, params = NULL, id = NULL) {
    msg <- list(jsonrpc = "2.0", method = method)
    if (!is.null(params)) msg$params <- params
    if (!is.null(id))     msg$id     <- id
    msg
  }

  # FastMCP always returns text/event-stream, even for single-message responses.
  # SSE format: one or more `data: {json}` lines, separated by blank lines.
  # This helper extracts the JSON from the first data frame.
  resp_body_mcp <- function(resp) {
    raw  <- httr2::resp_body_string(resp)
    lines <- strsplit(raw, "\n", fixed = TRUE)[[1]]
    data_lines <- lines[grepl("^data:", lines)]
    if (length(data_lines) == 0L) stop("MCP response contained no data lines")
    json_str <- sub("^data:\\s*", "", data_lines[[1L]])
    jsonlite::fromJSON(json_str, simplifyVector = FALSE)
  }

  # ---- 1. initialize --------------------------------------------------------

  init_resp <- new_req() |>
    httr2::req_body_json(jsonrpc(
      "initialize",
      id = 1L,
      params = list(
        protocolVersion = "2024-11-05",
        capabilities    = list(tools = list()),
        clientInfo      = list(name = "r-ellmer-mcp-bridge", version = "0.1.0")
      )
    )) |>
    httr2::req_perform()

  session_id <- httr2::resp_header(init_resp, "MCP-Session-Id")

  # ---- 2. initialized notification ------------------------------------------

  tryCatch(
    new_req(session_id) |>
      httr2::req_body_json(jsonrpc("notifications/initialized")) |>
      httr2::req_perform(),
    httr2_http_error = function(e) invisible(NULL),
    error            = function(e) invisible(NULL)
  )

  # ---- 3. list tools --------------------------------------------------------

  tools_raw <- new_req(session_id) |>
    httr2::req_body_json(jsonrpc("tools/list", id = 2L)) |>
    httr2::req_perform() |>
    resp_body_mcp()

  tools_list <- tools_raw$result$tools

  if (length(tools_list) == 0L) {
    warning("MCP server returned no tools.")
    return(list())
  }

  # ---- 4. convert each tool to an ellmer tool object ------------------------

  # Capture immutable state for use inside tool closures
  env <- new.env(parent = emptyenv())
  env$url        <- url
  env$auth       <- auth
  env$session_id <- session_id

  lapply(tools_list, function(tspec) {

    tool_name   <- tspec$name
    properties  <- tspec$inputSchema$properties %||% list()
    param_names <- names(properties)

    # Build ellmer argument type specs from the JSON schema.
    # ellmer's type_from_schema handles anyOf+null correctly.
    arguments <- setNames(
      lapply(param_names, function(pname) {
        ellmer::type_from_schema(
          jsonlite::toJSON(properties[[pname]], auto_unbox = TRUE)
        )
      }),
      param_names
    )

    # The function called by ellmer when the LLM invokes this tool.
    #
    # ellmer::tool() requires that the function's formal parameter names
    # match the names in `arguments`.  We use a generic body that captures
    # all named parameters via as.list(environment()), then override the
    # formals dynamically with the schema's parameter names so the names
    # align.
    call_fun <- function() {
      # Capture all formal parameters from the execution environment.
      # This must be the first expression so no other locals are present.
      call_args <- as.list(environment())
      # Drop NULLs — optional params the LLM chose not to supply
      call_args <- call_args[!vapply(call_args, is.null, logical(1L))]

      req <- httr2::request(env$url) |>
        httr2::req_method("POST") |>
        httr2::req_headers(
          "Content-Type" = "application/json",
          "Accept"       = "application/json, text/event-stream"
        )
      if (!is.null(env$auth))        req <- httr2::req_headers(req, "Authorization"  = env$auth)
      if (!is.null(env$session_id))  req <- httr2::req_headers(req, "MCP-Session-Id" = env$session_id)

      # Build params; omit `arguments` entirely when empty so the server
      # receives a JSON object rather than an empty array.
      params <- list(name = tool_name)
      if (length(call_args) > 0L) params$arguments <- call_args

      result <- req |>
        httr2::req_body_json(list(
          jsonrpc = "2.0",
          method  = "tools/call",
          id      = sample.int(1e6L, 1L),
          params  = params
        )) |>
        httr2::req_perform() |>
        resp_body_mcp()

      if (!is.null(result$error)) stop(result$error$message)

      # MCP content is an array of {type, text} items — join to one string
      content <- result$result$content %||% list()
      texts   <- vapply(content, function(c) c$text %||% "", character(1L))
      paste(texts, collapse = "\n")
    }

    # Replace the empty formals() with the tool's actual parameter names
    # (all defaulting to NULL so optional params can be omitted by the LLM).
    formals(call_fun) <- setNames(
      rep(list(NULL), length(param_names)),
      param_names
    )

    ellmer::tool(
      fun         = call_fun,
      description = tspec$description %||% tool_name,
      arguments   = arguments,
      name        = tool_name
    )
  })
}
