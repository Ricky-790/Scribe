---
name: Spectator Research Intelligence
colors:
  surface: '#111417'
  surface-dim: '#111417'
  surface-bright: '#37393e'
  surface-container-lowest: '#0c0e12'
  surface-container-low: '#191c20'
  surface-container: '#1d2024'
  surface-container-high: '#272a2e'
  surface-container-highest: '#323539'
  on-surface: '#e1e2e8'
  on-surface-variant: '#d3c4b1'
  inverse-surface: '#e1e2e8'
  inverse-on-surface: '#2e3135'
  outline: '#9c8f7d'
  outline-variant: '#4f4536'
  surface-tint: '#f5bd58'
  primary: '#f7bf59'
  on-primary: '#422c00'
  primary-container: '#d9a441'
  on-primary-container: '#573c00'
  inverse-primary: '#7d5700'
  secondary: '#98d3b2'
  on-secondary: '#003824'
  secondary-container: '#17533a'
  on-secondary-container: '#8ac5a5'
  tertiary: '#a7caff'
  on-tertiary: '#00315d'
  tertiary-container: '#7faff1'
  on-tertiary-container: '#004179'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdeaa'
  primary-fixed-dim: '#f5bd58'
  on-primary-fixed: '#271900'
  on-primary-fixed-variant: '#5f4100'
  secondary-fixed: '#b3f0cd'
  secondary-fixed-dim: '#98d3b2'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#145037'
  tertiary-fixed: '#d4e3ff'
  tertiary-fixed-dim: '#a4c9ff'
  on-tertiary-fixed: '#001c39'
  on-tertiary-fixed-variant: '#014883'
  background: '#111417'
  on-background: '#e1e2e8'
  surface-variant: '#323539'
typography:
  display-lg:
    fontFamily: Source Serif 4
    fontSize: 48px
    fontWeight: '600'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Source Serif 4
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Source Serif 4
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 30.6px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 27.2px
  label-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  mono-ui:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-max: 1120px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 48px
  section-gap: 80px
---

## Brand & Style

The design system is anchored in the concept of an "Intelligence Briefing." It moves away from high-energy tech aesthetics toward a grounded, editorial atmosphere that suggests depth, authority, and calm focus. The target audience is researchers, analysts, and decision-makers who require high information density presented with high legibility.

The style is **Premium Minimalist**. It utilizes a dark-mode-first approach with a palette inspired by physical archival materials—charcoal paper, brass hardware, and muted inks. Visual hierarchy is achieved through precise hairline borders and generous whitespace rather than shadows or depth. The emotional response is one of quiet confidence, clarity, and intellectual rigor.

## Colors

The palette is strictly curated to minimize cognitive load. The background uses a warm charcoal to reduce eye strain during long-form reading. 

- **Primary (Amber/Brass):** Reserved exclusively for high-priority actions, focus indicators, and key milestones in the AI research process. Use sparingly to maintain its "precious" quality.
- **Surface Tiers:** Layering is achieved by shifting from the base (#0E0F11) to slightly lighter charcoal tones. These are used for sidebars, cards, and modal backdrops.
- **Borders:** Hairlines (#2A2C30) are the primary structural element. They should be used for all dividers, input perimeters, and section separations.
- **Functional Colors:** Sage and Terracotta are desaturated to ensure they don't break the sophisticated editorial feel while still providing clear semantic status.

## Typography

This design system employs a "Serif for Substance, Sans for Utility" philosophy.

- **Source Serif 4:** Used for the "Output"—research findings, report headers, and quotes. It provides the intellectual, literary feel of a high-end publication.
- **Inter:** Used for the "Interface"—menus, buttons, input fields, and metadata. It ensures functional clarity and high legibility at small sizes.
- **Leading:** A generous line-height of 1.7x (represented as 30.6px for 18px body) is mandatory for all long-form text blocks to prevent visual crowding.
- **Labels:** Use uppercase with tracking for small labels to create a professional, "classified document" aesthetic.

## Layout & Spacing

The layout philosophy is centered on **Focus**. It uses a 12-column fixed grid for desktop content (max 1120px) to ensure reading lines do not become too wide, which would degrade legibility.

- **Grid:** On desktop, use a centered container. On mobile, use a single-column fluid layout with 16px margins.
- **Rhythm:** Spacing follows a 4px baseline, but defaults to larger jumps (24px, 48px, 80px) to maintain the "airy," premium feel.
- **Negative Space:** Empty space is treated as a design element. Research reports should have significant top and bottom padding to isolate the content from the UI chrome.

## Elevation & Depth

This design system avoids physical depth. There are no shadows, blurs, or gradients.

- **Tonal Separation:** Depth is expressed solely through background color shifts. A "Surface Raised" container (#1F2124) is used to denote elements that are interactive or temporarily overlaid (like a dropdown).
- **Hairlines:** 1px borders are used to define the edges of all containers. In "Surface Raised" states, the border remains constant, but the background color changes.
- **Interactions:** Hover states should be subtle, usually a slight change in border brightness or a very gentle background shift (e.g., from #17181B to #1F2124).

## Shapes

The shape language is precise and architectural. 

- **Corners:** We use a "Soft" (0.25rem) radius for standard components like buttons and inputs. This provides just enough friendliness to feel modern without losing the serious, professional edge of sharp corners.
- **Large Elements:** Cards and main content areas may use the `rounded-lg` (0.5rem) setting to create a distinct container feel within the broader layout.
- **Iconography:** Use 1.5pt stroke-weight outline icons with square caps to match the sharp-edged architectural feel of the UI.

## Components

- **Buttons:** Primary buttons are Solid Amber (#D9A441) with near-black text. Secondary buttons use a hairline border (#2A2C30) with no fill. Transitions must be a simple 200ms opacity fade.
- **Inputs:** Text fields use the Surface color (#17181B) with a 1px border. Focus is indicated by the border changing to Amber—no outer glow or shadow.
- **Chips/Tags:** Used for "Research Topics" or "Entities." These should be background-less with a hairline border and `label-sm` typography.
- **Research Cards:** Used for previewing reports. They feature a Source Serif 4 title, a short Inter description, and a thin border. 
- **AI Response Pulse:** When the AI is generating text, use a very subtle "breathing" opacity animation (0.6 to 1.0) on the cursor or a small amber dot, rather than a frantic loading spinner.
- **Lists:** Use horizontal hairline dividers between items. Avoid zebra-striping. Use generous vertical padding (16px+) for list items to maintain the premium feel.