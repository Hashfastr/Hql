# String functions

## tolower()
`tolower(x)` lowercases a string field or literal.
A literal is lowercased at compile time.

```
Database
| extend l = tolower("ABC"), l2 = tolower(b)    // l = "abc", b = "X" → l2 = "x"
```

## base64()
`base64(s [, encoding])` Base64 encodes a string.
Aliases: `b64`.

The string is first converted to bytes using `encoding`, which defaults to `ascii`.
Any Python codec name works, e.g. `'utf-8'` or `'utf-16le'`.

```
Database
| extend e = base64("hello")      // "aGVsbG8="
```

## base64dec()
`base64dec(s [, encoding])` decodes a Base64 string and turns the bytes back into text using `encoding` (default `ascii`).
Aliases: `b64dec`.
Invalid Base64 fails the query.

```
Database
| extend d = b64dec("aGVsbG8=")   // "hello"
```

## base64offset()
`base64offset(s [, encoding])` returns an array with the three Base64 fragments of `s`, one for each byte alignment (offset 0, 1 and 2).
Only the characters that stay stable at that alignment are kept.
This is the usual detection trick for finding a string inside a larger Base64 blob without knowing where it starts.
Aliases: `base64off`, `b64off`.

The intended use is `where field has_any (base64offset("..."))`.
At the moment the function only resolves at compile time, and using it in `extend` or `where` fails (workspace-rkh).

## wide()
`wide(s)` encodes a string literal as UTF-16LE bytes, the "wide" string format used by Windows.
The result is binary, e.g. `wide("hi")` gives the bytes `h\x00i\x00`.

Only literals are supported.
Combine it with `base64` to find wide strings inside encoded PowerShell, e.g. `base64(wide("..."))`.

## Applying to fields
`base64`, `base64dec`, `base64offset` and `wide` accept a field reference syntactically, but they only compute literal values.
Passing a field fails at runtime.
