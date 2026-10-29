# Hql features
This folder documents what Hql implements today.
The examples are real queries, and the outputs shown come from running them.
Anything the grammar accepts but that doesn't run yet is listed as unimplemented, not documented as working.

- [Operators](./Operators.md): tabular operators (`where`, `project`, `summarize`, `join`, ...)
- [Scalar operators](./Scalar-Operators.md): comparisons, string matching, arithmetic, logic and literals
- [Functions](./Functions.md): casting, string, time, aggregation, source and output functions

## Basics
An Hql query is a source followed by a pipeline of operators, each one separated by `|`.

```
database('json').file('t.json')
| where a > 1
| project a, b
| take 10
```

### Multiple tables
Hql passes a *set of named tables* through the pipeline, not a single table.
A source like `file('a.json', 'b.json')` or an Elasticsearch index pattern gives one table per file or index.
Every operator runs on each table separately.

```
database('json').file('t.json', 'u.json')
| project a

{
    "t.json": [{"a": 1}, {"a": 2}, {"a": 3}],
    "u.json": [{"a": 1}, {"a": 2}, {"a": 5}]
}
```

Some operators can target tables by name pattern (`take ... from`, `unnest ... on`, `union`, `rename`).
Patterns are glob style (`*`, `?`).
A name containing `.` or `-` has to be quoted with brackets, e.g. `['t.json']` or `['so-beats-*']`.

If a table is missing a field that an expression references, the table is usually skipped rather than raising an error.
`where`, for example, drops that table completely.

### Nested fields
Nested fields are addressed with dots (`source.ip`).
Names that aren't plain identifiers go in brackets (`['@timestamp']`).
Projecting a nested path keeps the nesting (`project o.p` gives `{"o": {"p": 1}}`).
Assigning it to a name gives a flat column (`project x = o.p` gives `{"x": 1}`).

### Let statements
`let` binds a name to a value or to a tabular expression.
Statements are separated by `;`.

```
let x = 2;
let tbl = database('json').file('t.json');
tbl
| where a == x
```
