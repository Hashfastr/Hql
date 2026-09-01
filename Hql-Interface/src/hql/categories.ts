const TYPE_WORDS = new Set([
  'bool', 'boolean', 'date', 'datetime', 'decimal', 'double', 'dynamic', 'float',
  'guid', 'int', 'int8', 'int16', 'int32', 'int64', 'long', 'real', 'string',
  'time', 'timespan', 'uint', 'uint8', 'uint16', 'uint32', 'uint64', 'ulong',
  'uniqueid', 'ip4', 'ip6',
])

export type Category = 'keyword' | 'type' | 'string' | 'literal' | 'comment' | 'operator'

export function tokenCategory(symbolic: string, literal?: string): Category | undefined {
  if (symbolic === 'COMMENT' || symbolic === 'MULTILINECOMMENT') return 'comment'

  if (
    symbolic === 'WHITESPACE' ||
    symbolic === 'IDENTIFIER'
  ) {
    return undefined
  }
  if (symbolic.includes('STRINGLITERAL')) return 'string'
  if (symbolic.endsWith('LITERAL')) return 'literal'
  if (literal && /^[a-zA-Z]/.test(literal)) {
    return TYPE_WORDS.has(literal) ? 'type' : 'keyword'
  }
  if (literal) return 'operator'
  return undefined
}
