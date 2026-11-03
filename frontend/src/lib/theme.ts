export type ThemeDesign = Record<string, any>

type RGB = { r: number; g: number; b: number; a: number }

const DEFAULT_DARK: RGB = { r: 15, g: 16, b: 38, a: 1 }

export function parseColor(input?: string | null): RGB | null {
  if (!input || typeof input !== 'string') return null
  const value = input.trim().toLowerCase()

  if (value.startsWith('#')) {
    let hex = value.slice(1)
    if (hex.length === 3) hex = hex.split('').map(c => c + c).join('')
    if (hex.length === 6 || hex.length === 8) {
      const r = parseInt(hex.slice(0, 2), 16)
      const g = parseInt(hex.slice(2, 4), 16)
      const b = parseInt(hex.slice(4, 6), 16)
      const a = hex.length === 8 ? parseInt(hex.slice(6, 8), 16) / 255 : 1
      if ([r, g, b, a].every(Number.isFinite)) return { r, g, b, a }
    }
    return null
  }

  const match = value.match(/^rgba?\(([^)]+)\)$/)
  if (match) {
    const parts = match[1].split(',').map(p => parseFloat(p.trim()))
    if (parts.length >= 3 && parts.slice(0, 3).every(Number.isFinite)) {
      const a = parts.length > 3 && Number.isFinite(parts[3]) ? parts[3] : 1
      return { r: parts[0], g: parts[1], b: parts[2], a }
    }
  }
  return null
}

function toCss({ r, g, b, a }: RGB): string {
  const clamp = (n: number) => Math.max(0, Math.min(255, Math.round(n)))
  return a < 1 ? `rgba(${clamp(r)}, ${clamp(g)}, ${clamp(b)}, ${a})` : `rgb(${clamp(r)}, ${clamp(g)}, ${clamp(b)})`
}

function opaque(color: RGB, base: RGB): RGB {
  if (color.a >= 1) return color
  return {
    r: color.r * color.a + base.r * (1 - color.a),
    g: color.g * color.a + base.g * (1 - color.a),
    b: color.b * color.a + base.b * (1 - color.a),
    a: 1,
  }
}

function mix(a: RGB, b: RGB, weight: number): RGB {
  const w = Math.max(0, Math.min(1, weight))
  return {
    r: a.r * (1 - w) + b.r * w,
    g: a.g * (1 - w) + b.g * w,
    b: a.b * (1 - w) + b.b * w,
    a: 1,
  }
}

function relativeLuminance(color: RGB): number {
  const channel = (v: number) => {
    const c = v / 255
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
  }
  return 0.2126 * channel(color.r) + 0.7152 * channel(color.g) + 0.0722 * channel(color.b)
}

function contrast(a: RGB, b: RGB): number {
  const l1 = relativeLuminance(a)
  const l2 = relativeLuminance(b)
  const light = Math.max(l1, l2)
  const dark = Math.min(l1, l2)
  return (light + 0.05) / (dark + 0.05)
}

function readableText(background: RGB, preferred?: string): string {
  const preferredRgb = parseColor(preferred)
  if (preferredRgb) {
    const preferredOpaque = opaque(preferredRgb, background)
    if (contrast(preferredOpaque, background) >= 4.5) return preferred as string
  }
  const white = { r: 255, g: 255, b: 255, a: 1 }
  const black = { r: 17, g: 17, b: 17, a: 1 }
  return contrast(white, background) >= contrast(black, background) ? '#ffffff' : '#111111'
}

function colorFromGradient(gradient?: string | null): RGB | null {
  if (!gradient) return null
  const matches = gradient.match(/#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)/g)
  if (!matches || matches.length === 0) return null
  const colors = matches.map(parseColor).filter(Boolean) as RGB[]
  if (colors.length === 0) return null
  const opaqueColors = colors.map(c => opaque(c, DEFAULT_DARK))
  const avg = opaqueColors.reduce(
    (acc, c) => ({ r: acc.r + c.r / opaqueColors.length, g: acc.g + c.g / opaqueColors.length, b: acc.b + c.b / opaqueColors.length, a: 1 }),
    { r: 0, g: 0, b: 0, a: 1 },
  )
  return avg
}

/**
 * Applies a design configuration to the document using the shared CSS
 * variables.  Works for dark, light, gradient, translucent and custom themes.
 */
export function applyTheme(design: ThemeDesign = {}, root: HTMLElement = document.documentElement) {
  const bgColor = parseColor(design.bg_color) || DEFAULT_DARK
  const gradientColor = design.bg_type === 'gradient' ? colorFromGradient(design.bg_gradient) : null
  const baseBg = opaque(gradientColor || bgColor, DEFAULT_DARK)
  const isDark = relativeLuminance(baseBg) < 0.45

  const rawCard = parseColor(design.card_color) || (isDark ? { r: 31, g: 34, b: 55, a: 1 } : { r: 255, g: 255, b: 255, a: 1 })
  const cardOpaque = opaque(rawCard, baseBg)
  const text = parseColor(design.text_color) || (isDark ? { r: 244, g: 244, b: 249, a: 1 } : { r: 33, g: 37, b: 41, a: 1 })
  const textColor = readableText(cardOpaque, toCss(text))
  const textRgb = parseColor(textColor) || text

  const accent = parseColor(design.accent_color) || { r: 124, g: 58, b: 237, a: 1 }
  const accentOpaque = opaque(accent, baseBg)

  const inputBg = mix(cardOpaque, textRgb, isDark ? 0.06 : 0.03)
  const optionBg = mix(cardOpaque, baseBg, 0.08)
  const optionHoverBg = mix(optionBg, accentOpaque, 0.22)
  const optionSelectedBg = mix(optionBg, accentOpaque, 0.45)

  const set = (name: string, value: string) => root.style.setProperty(name, value)

  const backgroundImage = design.bg_image_url
    ? `url("${design.bg_image_url}")`
    : design.bg_type === 'gradient' && design.bg_gradient
      ? design.bg_gradient
      : 'none'

  set('--q-bg', toCss(baseBg))
  set('--q-bg-image', backgroundImage)
  set('--q-bg-position', design.bg_position || 'center')
  set('--q-bg-size', design.bg_size || 'cover')

  set('--q-text', textColor)
  set('--q-heading', readableText(cardOpaque, design.heading_color || '#ffffff'))
  set('--q-accent', toCss(accentOpaque))
  set('--q-card', toCss(rawCard))
  set('--q-card-opaque', toCss(cardOpaque))
  set('--q-radius', design.radius || '12px')

  set('--q-input-bg', toCss(inputBg))
  set('--q-input-text', readableText(inputBg, textColor))
  set('--q-option-bg', toCss(optionBg))
  set('--q-option-text', readableText(optionBg, textColor))
  set('--q-option-hover-bg', toCss(optionHoverBg))
  set('--q-option-selected-bg', toCss(optionSelectedBg))
  set('--q-option-selected-text', readableText(optionSelectedBg, textColor))
  set('--q-placeholder', `rgba(${Math.round(textRgb.r)}, ${Math.round(textRgb.g)}, ${Math.round(textRgb.b)}, 0.6)`)
  set('--q-border', `rgba(${Math.round(textRgb.r)}, ${Math.round(textRgb.g)}, ${Math.round(textRgb.b)}, 0.18)`)
  set('--q-menu-bg', toCss(optionBg))
  set('--q-menu-text', readableText(optionBg, textColor))

  set('--q-btn-text', readableText(accentOpaque, '#ffffff'))
  set('--q-success', isDark ? '#4ade80' : '#15803d')
  set('--q-danger', isDark ? '#f87171' : '#b91c1c')
  set('--q-warning', isDark ? '#fbbf24' : '#b45309')

  set('--q-font', design.font_family || 'Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif')
  set('--q-font-size', design.font_size || '16px')
  set('--q-line-height', design.line_height || '1.6')
  set('--q-content-width', design.content_width || '760px')
  set('--q-gap', design.gap || '16px')
  set('--q-card-blur', design.card_blur || '0px')
  set('--q-card-border', `${design.card_border_width || '0px'} solid ${design.card_border_color || 'rgba(255,255,255,0.3)'}`)
  set('--q-card-shadow', design.card_shadow || 'none')

  root.style.setProperty('color-scheme', relativeLuminance(inputBg) < 0.45 ? 'dark' : 'light')
  root.dataset.theme = isDark ? 'dark' : 'light'
}
