/**
 * Build a lookup from Unicode code-point offsets to JavaScript/CodeMirror
 * UTF-16 offsets. ANTLR's CharStream counts code points, while CodeMirror
 * addresses documents in UTF-16 code units.
 */
export function codePointBoundaries(text: string): number[] {
  const boundaries = [0]
  let codeUnitOffset = 0

  for (const codePoint of text) {
    codeUnitOffset += codePoint.length
    boundaries.push(codeUnitOffset)
  }

  return boundaries
}

export function codeUnitOffset(boundaries: number[], codePointOffset: number): number {
  const index = Math.max(0, Math.min(codePointOffset, boundaries.length - 1))
  return boundaries[index]
}
