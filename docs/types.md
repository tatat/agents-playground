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
