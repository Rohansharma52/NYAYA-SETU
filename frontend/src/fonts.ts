/**
 * Self-hosted fonts so the UI looks the same without internet (e.g. at the venue).
 * Vite bundles these only when the @fontsource packages are installed; when they are
 * missing the glob resolves to nothing and the Google Fonts link in index.html is used.
 */
type Glob = { glob: (patterns: string[], options: { eager: true; exhaustive: true }) => Record<string, unknown> }

;(import.meta as unknown as Glob).glob(
  [
    '/node_modules/@fontsource/plus-jakarta-sans/{400,500,600,700,800}.css',
    '/node_modules/@fontsource/cinzel/{600,700,800}.css',
    '/node_modules/@fontsource/jetbrains-mono/{400,500,600}.css',
    '/node_modules/@fontsource/noto-serif-devanagari/{500,600,700}.css',
  ],
  { eager: true, exhaustive: true },
)

export {}
