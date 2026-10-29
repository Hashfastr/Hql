# project
The `project` operator chooses which fields the output keeps, and can compute new ones.
Only the listed fields remain, in the order they're listed.

Each entry is either:
- a field reference, `a` or `o.p`, which keeps the field (a nested path keeps its nesting)
- an assignment, `name = expression`, which creates a field from a reference, literal, arithmetic expression or function

Literals are repeated on every row.

```
datatable (a:int, b:string) [1, "x", 2, "y"]
| project a, c = a * 2

{
    "datatable": [{"a": 1, "c": 2}, {"a": 2, "c": 4}]
}

// Nested paths
Database
| project a, o.p      // [{"a": 1, "o": {"p": 1}}, ...]

Database
| project x = o.p     // [{"x": 1}, ...]

// Literals and names that need quoting
Database
| project ['@timestamp'], kind = "event", one = 1
```

## project-away
Removes the listed fields and keeps all the others.
Fields can be nested paths.

```
datatable (a:int, b:string) [1, "x", 2, "y"]
| project-away b

{
    "datatable": [{"a": 1}, {"a": 2}]
}
```

## project-keep
Works the same as `project`, it's kept for Kusto compatibility.

```
datatable (a:int, b:string) [1, "x", 2, "y"]
| project-keep b

{
    "datatable": [{"b": "x"}, {"b": "y"}]
}
```

## project-rename
Renames fields with `new_name = existing_name`.
Values, types and all the other fields stay as they are.
Every rename reads its source before any field is dropped, so swaps like `project-rename a = b, b = a` work.

```
datatable (a:int, b:string) [1, "x", 2, "y"]
| project-rename c = a

{
    "datatable": [{"c": 1, "b": "x"}, {"c": 2, "b": "y"}]
}
```

## project-reorder
Moves the listed fields to the front, in the order given.
The remaining fields follow after them.

```
datatable (a:int, b:string) [1, "x", 2, "y"]
| project-reorder b

{
    "datatable": [{"b": "x", "a": 1}, {"b": "y", "a": 2}]
}
```

Kusto's `asc`/`desc` sort modifiers for `project-reorder` don't parse yet (workspace-49p).
