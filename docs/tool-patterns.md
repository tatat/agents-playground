# Tool Patterns

Tool calling patterns for LLM agents.

## Tool Search

Dynamic tool discovery pattern for agents with many tools (30-50+).

### Problem

- **Context bloat**: All tool definitions consume tokens
- **Selection errors**: LLM struggles to choose the right tool

### Two Approaches

| Aspect | Filter Pattern | Interrupt Pattern |
|--------|---------------|-------------------|
| Complexity | Simpler | More complex |
| Token saving | Yes | Yes |
| Tool registration | All upfront | Dynamic |
| Use case | Known tool set | Truly dynamic tools |
| State management | Middleware state | Checkpointer required |
| Notebook | `tool-search-filter.ipynb` | `tool-search-interrupt.ipynb` |

---

### Filter Pattern

Register all tools upfront, use middleware to filter which tools are visible to the LLM.

**When to use**: Tool set is known at startup, just need to reduce context.

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant Middleware
    participant ToolRegistry

    User->>Agent: "What's the weather in Tokyo?"

    Note over Agent: All tools registered<br/>but only tool_search visible

    Agent->>Agent: Call tool_search("weather")
    Agent->>ToolRegistry: Pattern match search
    ToolRegistry-->>Agent: [get_weather, get_forecast]

    Middleware->>Middleware: Track discovered tools
    Note over Middleware: discovered_tools += {get_weather, get_forecast}

    Note over Agent: Next model call:<br/>tool_search + get_weather + get_forecast visible

    Agent->>Agent: Call get_weather("Tokyo")
    Agent-->>User: "Tokyo: Sunny, 22°C"
```

#### Key Points

1. **All tools registered**: `create_agent(tools=[tool_search, *ALL_TOOLS])`
2. **Middleware filters visibility**: `wrap_model_call` filters `request.tools`
3. **No interrupt needed**: Same agent instance throughout
4. **State in middleware**: `discovered_tools: set[str]` persists naturally

---

### Interrupt Pattern

Start with only `tool_search`, use middleware to interrupt and recreate agent with discovered tools.

**When to use**: Tools loaded from external sources, cannot enumerate upfront.

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant Middleware
    participant ToolRegistry

    User->>Agent: "What's the weather in Tokyo?"

    Note over Agent: Initial state: only tool_search

    Agent->>Agent: Call tool_search("weather")
    Agent->>ToolRegistry: Pattern match search
    ToolRegistry-->>Agent: [get_weather]

    Agent->>Middleware: Process tool result
    Middleware->>Middleware: Discover new tools
    Middleware->>Middleware: interrupt()

    Note over Middleware: discovered_tools: [get_weather]

    Middleware->>Agent: Recreate agent<br/>(add discovered tools)

    Note over Agent: Updated: tool_search + get_weather

    Agent->>Agent: Resume with Command(resume)
    Agent->>Agent: Call get_weather("Tokyo")
    Agent-->>User: "Tokyo: Sunny, 22°C"
```

#### Components

```mermaid
graph TB
    subgraph "Agent Layer"
        A[Agent<br/>tool_search only]
        A2[Agent<br/>+ discovered tools]
    end

    subgraph "Middleware Layer"
        M[DynamicToolMiddleware]
        M -->|wrap_tool_call| TC[Monitor tool calls]
        TC -->|if tool_search| D[Track discovered tools]
        D -->|on new discovery| I[interrupt]
    end

    subgraph "Tool Layer"
        TS[tool_search]
        TR[(ToolRegistry)]
        T1[get_weather]
        T2[send_email]
        T3[query_sales]
        T4[...]
    end

    A --> M
    M --> TS
    TS --> TR
    TR -.-> T1
    TR -.-> T2
    TR -.-> T3

    I -->|recreate| A2
    A2 --> T1
```

#### Key Points

1. **ToolRegistry**: Holds all tools (name → BaseTool)
2. **tool_search**: Search tools by regex, return schemas
3. **DynamicToolMiddleware**: Monitor results via `wrap_tool_call`
4. **interrupt**: Pause on new discovery, recreate agent

#### Limitations

- **No dynamic tool injection**: LangGraph agents cannot add tools at runtime. The agent must be recreated with the new tool set.
- **Checkpointer required**: A shared `InMemorySaver` (or persistent checkpointer) is needed to preserve conversation state across agent recreation.
- **Interrupt/resume overhead**: Each tool discovery triggers an interrupt → recreate → resume cycle.

---

### Failed Approach: Middleware Tool Injection

See `dynamic-tools-failed.ipynb` for why injecting new `BaseTool` via middleware doesn't work.

**TL;DR**: Middleware can modify `request.tools`, but the tools node only knows about tools registered at `create_agent()` time. Injecting a tool the agent wasn't created with causes `ValueError: Middleware returned unknown tool names`.

**Exception**: `dict` format tools (Anthropic server-side tools like `web_search`) can be added dynamically because they execute server-side, not locally.

---

## Programmatic Tool Calling

Batch execute multiple tool calls to reduce API round-trips.

### Problem

- **Latency**: API round-trip for each tool call
- **Token overhead**: Intermediate results returned to model every time

### Solution

Agent generates Python code, executes in sandbox.
Batch multiple tool calls, return only final result.

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant Sandbox
    participant Tools

    User->>Agent: "Compare sales and weather for all regions"

    Agent->>Agent: tool_search("sales|weather")
    Note over Agent: Discover query_sales, get_weather

    Agent->>Agent: Generate Python code

    Note over Agent: Code example:<br/>for region in regions:<br/>  sales = await tool_call("query_sales", region=region)<br/>  weather = await tool_call("get_weather", city=capitals[region])<br/>  print(f"{region}: {sales}, {weather}")

    Agent->>Sandbox: execute_code(code)

    loop Each tool call
        Sandbox->>Sandbox: Write JSON-RPC request to stdout
        Sandbox->>Tools: {"jsonrpc":"2.0","method":"...","params":{...},"id":N}
        Tools-->>Sandbox: {"jsonrpc":"2.0","result":{...},"id":N}
    end

    Sandbox->>Sandbox: Send print notifications
    Sandbox-->>Agent: Collected print output

    Agent-->>User: "Analysis: West region is optimal..."
```

### Architecture

```mermaid
graph TB
    subgraph "Agent"
        A[LLM Agent]
        TS[tool_search]
        EC[execute_code]
    end

    subgraph "Sandbox Runtime (srt)"
        S[Python Sandbox]
        TC[tool_call function]
        P[print function<br/>capture output]
    end

    subgraph "Host Process"
        H[Tool Handler]
        TR[(ToolRegistry)]
    end

    A -->|1. Search tools| TS
    TS --> TR

    A -->|2. Generate code| EC
    EC -->|stdin/stdout| S

    S --> TC
    TC -->|JSON-RPC request| H
    H --> TR
    TR -->|execute| T1[query_sales]
    TR -->|execute| T2[get_weather]
    H -->|JSON-RPC response| TC

    S --> P
    P -->|JSON-RPC notification| EC
    EC -->|final output| A
```

### Communication Protocol (JSON-RPC 2.0)

```mermaid
sequenceDiagram
    participant Code as Sandbox Code
    participant Stdout as stdout
    participant Host as Host Process
    participant Stdin as stdin

    Code->>Stdout: {"jsonrpc":"2.0","method":"query_sales","params":{"region":"west"},"id":1}
    Stdout->>Host: Receive request
    Host->>Host: Execute tool
    Host->>Stdin: {"jsonrpc":"2.0","result":{"revenue":150000,...},"id":1}
    Stdin->>Code: Receive result

    Note over Code: Next tool call...

    Code->>Stdout: {"jsonrpc":"2.0","method":"print","params":{"text":"West: $150,000"}}
    Note over Stdout: Notification (no id)
    Code->>Stdout: {"jsonrpc":"2.0","method":"print","params":{"text":"East: $220,000"}}
```

### Benefits

| Aspect | Traditional | Programmatic |
|--------|-------------|--------------|
| API calls | N tools × round-trips | 1 round-trip |
| Tokens | All intermediate results | Final output only |
| Flexibility | Fixed flow | Loops, conditionals |

### Key Implementation Points

1. **srt (sandbox-runtime)**: Anthropic's sandbox execution environment
2. **tool_call()**: Function to invoke host tools from sandbox
3. **JSON-RPC 2.0**: Standard protocol over stdout/stdin (request with id, notification without id)
4. **print() capture**: Sent as JSON-RPC notification, collected by host

---

## Comparison

| Pattern | Problem | Solution |
|---------|---------|----------|
| Tool Search | Too many tools → context bloat | Dynamic discovery |
| Programmatic | Too many API calls → latency | Batch execution in sandbox |

These patterns solve different problems and can be used independently or together.

## References

- [Anthropic: Programmatic Tool Calling](https://platform.claude.com/docs/agents-and-tools/tool-use/programmatic-tool-calling)
- [sandbox-runtime](https://github.com/anthropic-experimental/sandbox-runtime)
