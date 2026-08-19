---
name: V-Velocity Kinetic
colors:
  surface: '#f9f9f9'
  surface-dim: '#dadada'
  surface-bright: '#f9f9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3f3'
  surface-container: '#eeeeee'
  surface-container-high: '#e8e8e8'
  surface-container-highest: '#e2e2e2'
  on-surface: '#1a1c1c'
  on-surface-variant: '#444653'
  inverse-surface: '#2f3131'
  inverse-on-surface: '#f1f1f1'
  outline: '#747685'
  outline-variant: '#c4c5d6'
  surface-tint: '#3154c9'
  primary: '#00237a'
  on-primary: '#ffffff'
  primary-container: '#0035ad'
  on-primary-container: '#97abff'
  inverse-primary: '#b7c4ff'
  secondary: '#5c5f61'
  on-secondary: '#ffffff'
  secondary-container: '#e1e2e6'
  on-secondary-container: '#626567'
  tertiary: '#2d2d2d'
  on-tertiary: '#ffffff'
  tertiary-container: '#434343'
  on-tertiary-container: '#b2afaf'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dde1ff'
  primary-fixed-dim: '#b7c4ff'
  on-primary-fixed: '#001552'
  on-primary-fixed-variant: '#0b3ab1'
  secondary-fixed: '#e1e2e6'
  secondary-fixed-dim: '#c5c6ca'
  on-secondary-fixed: '#191c1e'
  on-secondary-fixed-variant: '#44474a'
  tertiary-fixed: '#e5e2e1'
  tertiary-fixed-dim: '#c8c6c5'
  on-tertiary-fixed: '#1c1b1b'
  on-tertiary-fixed-variant: '#474646'
  background: '#f9f9f9'
  on-background: '#1a1c1c'
  surface-variant: '#e2e2e2'
  electric-blue: '#0055FF'
  chrome-gradient-start: '#E6E7E8'
  chrome-gradient-end: '#A7A9AC'
  surface-white: '#FFFFFF'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 64px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-xl:
    fontFamily: Plus Jakarta Sans
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.3'
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.2'
    letterSpacing: 0.05em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.2'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  margin-mobile: 20px
  margin-desktop: 80px
  gutter: 24px
  section-gap: 120px
---

## Brand & Style

The design system is engineered to evoke the precision of high-performance electric vehicles and the forward momentum of sustainable technology. It targets a tech-savvy, eco-conscious audience that values premium craftsmanship and innovation.

The visual style is **Corporate / Modern** with a **Glassmorphic** edge. It utilizes expansive whitespace, high-fidelity automotive photography, and subtle light-refractive properties to mimic the surface of polished chrome and glass. The aesthetic is defined by "Kinetic Tension"—the intersection of sharp, geometric lines and sweeping, aerodynamic curves found in automotive silhouettes. 

Every interaction should feel frictionless and intentional, reflecting a commitment to a smart, electrified future.

## Colors

The palette is anchored by **VinFast Blue**, representing depth, trust, and electrical energy. This is supported by a sophisticated spectrum of **Silver/Chrome** tones that provide a metallic, high-tech texture to the interface.

- **Primary:** VinFast Blue (#0035AD) is used for brand anchors, primary actions, and key navigation highlights.
- **Secondary:** Silver (#A7A9AC) is used for decorative borders, inactive states, and metallic accents.
- **Surface Strategy:** The UI primarily uses a clean white background to emphasize spaciousness, with secondary sections utilizing a subtle chrome-to-white gradient to create a sense of depth and luster.
- **Functional Colors:** Text is rendered in deep charcoal (#121212) rather than pure black to maintain a softer, premium feel.

## Typography

The typography system balances modern approachability with technical precision.

- **Headlines:** Uses **Plus Jakarta Sans**. It provides a contemporary, friendly yet premium feel. Bold weights and tight letter-spacing for large displays mimic the impactful branding on vehicle rears.
- **Body:** Uses **Inter**. Chosen for its exceptional legibility across digital devices and its neutral, systematic character that doesn't distract from high-quality imagery.
- **Labels/Technical Data:** Uses **JetBrains Mono**. This monospaced font is used sparingly for categories, timestamps, and technical specifications (e.g., range, acceleration) to reinforce the high-tech, engineered nature of the brand.

## Layout & Spacing

This design system employs a **Fixed Grid** philosophy for desktop to maintain a controlled, editorial feel, transitioning to a fluid layout for mobile devices.

- **Desktop:** 12-column grid with a maximum content width of 1280px. Large margins (80px) ensure the content feels premium and uncrowded.
- **Mobile:** 4-column fluid grid with 20px margins.
- **Rhythm:** An 8px base unit drives all spacing. For editorial content, "Section Gaps" of 120px are encouraged to provide breathing room between distinct stories or product features.
- **Reflow:** On tablet, the 12-column grid collapses to 8 columns, with image-heavy cards shifting from horizontal to vertical stacks.

## Elevation & Depth

Hierarchy is achieved through **Tonal Layers** and **Glassmorphism**, rather than traditional heavy shadows.

- **Surface Tiers:** Backgrounds are primarily white (#FFFFFF). Secondary content containers use a very light gray (#F4F4F4) with subtle 1px chrome-colored outlines (#E6E7E8).
- **Glassmorphism:** Navigation bars and floating action cards use a backdrop blur (20px) with a 60% transparent white fill. This creates a sense of light passing through high-quality materials.
- **Soft Glows:** Primary buttons and active states may use a very soft, diffused VinFast Blue glow (15% opacity) to simulate the LED lighting found in electric vehicle interiors.
- **Depth:** Elements closer to the user are lighter and have more pronounced "glass" reflectivity.

## Shapes

The shape language is "Aerodynamic Geometric." It avoids overly aggressive sharp corners while shunning the "bubbly" look of consumer social apps.

- **General Corner Radius:** 0.5rem (8px) for cards and inputs to provide a modern, balanced feel.
- **Large Components:** Hero sections and large image containers use 1rem (16px) or 1.5rem (24px) for a more "molded" look.
- **Buttons:** Use a hybrid approach—standard buttons are rounded (8px), but primary call-to-actions can use a "pill" shape (rounded-full) to stand out as touch-friendly, ergonomic elements.
- **Visual Motif:** Subtle use of 45-degree chamfered corners on secondary decorative elements to mimic automotive venting.

## Components

- **Buttons:** Primary buttons use a solid VinFast Blue fill with white text. Secondary buttons use a "Chrome" ghost style: a 1px metallic border with a subtle gradient hover effect.
- **Cards:** Blog cards feature edge-to-edge photography at the top. The container has a subtle 1px border. On hover, the image should scale slightly (1.05x) to create a "zoom" effect without moving the layout.
- **Inputs:** Clean, 1px bordered boxes that transition to a VinFast Blue border on focus. Labels use the JetBrains Mono "Label-sm" style for a technical look.
- **Chips/Tags:** Used for blog categories (e.g., #Sustainability, #Innovation). These are styled with a light gray background and no border, using uppercase monospaced text.
- **Progressive Disclosure:** Use clean, minimalist icons (thin-line weight) for accordions and carousels, avoiding heavy fills.
- **Photography:** All imagery must be high-resolution with a consistent "cool" color temperature, emphasizing lighting reflections on car surfaces.