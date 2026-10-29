# extend
The `extend` operator adds computed fields and keeps every existing field.
Each entry is `name = expression`.
If the name already exists, the field is replaced with the new value.

New fields are placed before the existing ones in the output.

```
datatable (a:int, b:string) [1, "x", 2, "y"]
| extend c = a + 10, a = a * 100

{
    "datatable": [{"c": 11, "a": 100, "b": "x"}, {"c": 12, "a": 200, "b": "y"}]
}

// Functions and literals
Database
| extend t = todatetime(ts), n = len(tags), source = "edr"
```

Assignments in a single `extend` are independent of each other.
To use a field created by `extend` in a later expression, put it in a second `extend` (or a `where`, `project`, ...).
