# Type Annotations

## Guidelines

- Avoid `type: ignore` as much as possible

## `create_agent` Return Type

Use `CompiledStateGraph[Any]` for the return type.

```python
from typing import Any
from langgraph.graph.state import CompiledStateGraph

agent: CompiledStateGraph[Any] = create_agent(...)
```

### `CompiledStateGraph` Type Parameters

```python
CompiledStateGraph[StateT, ContextT, InputT, OutputT]
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `StateT` | Graph state schema | (required) |
| `ContextT` | Runtime context | `None` |
| `InputT` | Input schema | `StateT` |
| `OutputT` | Output schema | `StateT` |

Only `StateT` is required. Use `Any` for simplicity.

## `RunnableConfig` Type

Use `RunnableConfig` for agent configuration with `thread_id`. It's a `TypedDict` so you can assign dict literals directly.

```python
from langchain_core.runnables import RunnableConfig

config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
```

No `cast()` needed.
