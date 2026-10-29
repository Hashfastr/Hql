# rename
The `rename` operator renames tables, not fields.
The syntax is `rename source to destination, ...`.
Tables that aren't listed keep their names, and a source name that doesn't exist is ignored.
This is an Hql specific operator.

To rename fields, use [project-rename](./Project.md#project-rename).

```
database('json').file('t.json')
| project a, b
| rename ['t.json'] to events

{
    "events": [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}, {"a": 3, "b": ""}]
}
```

Table names that are keywords (such as the default `datatable` name) can't be used as a bare name here.
Give the source an explicit name with `as` instead.
