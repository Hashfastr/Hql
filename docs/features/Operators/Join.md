# join
The `join` operator joins every table in the pipeline (the left side) with the result of another query (the right side).
The syntax is `join [kind=KIND] (right side query) on field, ...`.

The right side is a full query in parentheses, and it can have its own pipeline.
Rows are matched on equality of the `on` fields, which must exist on both sides under the same name.
Nested paths work.

For the kinds that only keep right rows matching a left key, Hql first collects the distinct left keys.
It then pushes them to the right side as a filter, so the right database returns only the rows that can match.

## Kinds
| Kind | Result |
| --- | --- |
| `inner` (default) | all matching pairs |
| `innerunique` | like `inner`, but duplicate left keys are dropped first |
| `leftouter` | all left rows, right fields null where there's no match |
| `rightouter` | all right rows, left fields null where there's no match |
| `fullouter` | all rows from both sides. The keys aren't merged, the right key comes out as `<key>_right` |
| `leftsemi` | left rows that have a match, left fields only |
| `rightsemi` | right rows that have a match, right fields only |
| `leftanti` | left rows with no match, left fields only |
| `rightanti` | right rows with no match, right fields only |

The default is `inner`.
In Kusto the default is `innerunique`, so pass `kind=innerunique` explicitly when you want Kusto's behavior.

```
// t.json: a = 1, 2, 3     u.json: {a: 1, k: "one"}, {a: 2, k: "two"}, {a: 5, k: "five"}
database('json').file('t.json')
| project a
| join (database('json').file('u.json')) on a

{
    "t.json": [{"a": 1, "k": "one"}, {"a": 2, "k": "two"}]
}

database('json').file('t.json')
| project a
| join kind=leftouter (database('json').file('u.json')) on a

{
    "t.json": [{"a": 1, "k": "one"}, {"a": 2, "k": "two"}, {"a": 3, "k": null}]
}

database('json').file('t.json')
| project a
| join kind=leftanti (database('json').file('u.json')) on a

{
    "t.json": [{"a": 3}]
}

// Filtering the right side
database('json').file('t.json')
| project a
| join (database('json').file('u.json') | where k == "one") on a
```

Each left table is joined with every right table, and the output keeps the left table's name.
Kusto's `$left.x == $right.y` syntax isn't supported, and neither is a trailing `where` clause after `on`.
