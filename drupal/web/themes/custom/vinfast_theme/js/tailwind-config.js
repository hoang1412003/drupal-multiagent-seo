/**
 * Tailwind Configuration for VinFast Theme (V-Velocity Kinetic).
 */
if (typeof tailwind !== 'undefined') {
  tailwind.config = {
    darkMode: 'class',
    theme: {
      extend: {
        colors: {
          'primary': '#00237a',
          'primary-container': '#0035ad',
          'on-primary': '#ffffff',
          'on-primary-container': '#97abff',
          'primary-fixed': '#dde1ff',
          'primary-fixed-dim': '#b7c4ff',
          'on-primary-fixed': '#001552',
          'on-primary-fixed-variant': '#0b3ab1',
          'inverse-primary': '#b7c4ff',

          'secondary': '#5c5f61',
          'secondary-container': '#e1e2e6',
          'on-secondary': '#ffffff',
          'on-secondary-container': '#626567',
          'secondary-fixed': '#e1e2e6',
          'secondary-fixed-dim': '#c5c6ca',
          'on-secondary-fixed': '#191c1e',
          'on-secondary-fixed-variant': '#44474a',

          'tertiary': '#2d2d2d',
          'tertiary-container': '#434343',
          'on-tertiary': '#ffffff',
          'on-tertiary-container': '#b2afaf',
          'tertiary-fixed': '#e5e2e1',
          'tertiary-fixed-dim': '#c8c6c5',
          'on-tertiary-fixed': '#1c1b1b',
          'on-tertiary-fixed-variant': '#474646',

          'surface': '#f9f9f9',
          'surface-bright': '#f9f9f9',
          'surface-dim': '#dadada',
          'surface-white': '#ffffff',
          'surface-variant': '#e2e2e2',
          'surface-container-lowest': '#ffffff',
          'surface-container-low': '#f3f3f3',
          'surface-container': '#eeeeee',
          'surface-container-high': '#e8e8e8',
          'surface-container-highest': '#e2e2e2',
          'surface-tint': '#3154c9',

          'on-surface': '#1a1c1c',
          'on-surface-variant': '#444653',
          'inverse-surface': '#2f3131',
          'inverse-on-surface': '#f1f1f1',

          'outline': '#747685',
          'outline-variant': '#c4c5d6',
          'background': '#f9f9f9',
          'on-background': '#1a1c1c',

          'electric-blue': '#0055FF',
          'chrome-gradient-start': '#E6E7E8',
          'chrome-gradient-end': '#A7A9AC',

          'error': '#ba1a1a',
          'on-error': '#ffffff',
          'error-container': '#ffdad6',
          'on-error-container': '#93000a'
        },
        borderRadius: {
          'DEFAULT': '0.25rem',
          'sm': '0.25rem',
          'md': '0.5rem',
          'lg': '0.5rem',
          'xl': '0.75rem',
          '2xl': '1rem',
          '3xl': '1.5rem',
          'full': '9999px'
        },
        spacing: {
          'base': '8px',
          'gutter': '24px',
          'margin-mobile': '20px',
          'margin-desktop': '80px',
          'section-gap': '80px',
          'section-gap-lg': '120px'
        },
        fontFamily: {
          'display-lg': ['Plus Jakarta Sans', 'sans-serif'],
          'headline-xl': ['Plus Jakarta Sans', 'sans-serif'],
          'headline-lg': ['Plus Jakarta Sans', 'sans-serif'],
          'headline-lg-mobile': ['Plus Jakarta Sans', 'sans-serif'],
          'body-lg': ['Inter', 'sans-serif'],
          'body-md': ['Inter', 'sans-serif'],
          'label-md': ['JetBrains Mono', 'monospace'],
          'label-sm': ['JetBrains Mono', 'monospace']
        },
        fontSize: {
          'display-lg': ['64px', { lineHeight: '1.1', letterSpacing: '-0.02em', fontWeight: '700' }],
          'headline-xl': ['48px', { lineHeight: '1.2', letterSpacing: '-0.01em', fontWeight: '700' }],
          'headline-lg': ['32px', { lineHeight: '1.3', fontWeight: '600' }],
          'headline-lg-mobile': ['28px', { lineHeight: '1.3', fontWeight: '600' }],
          'body-lg': ['18px', { lineHeight: '1.6', fontWeight: '400' }],
          'body-md': ['16px', { lineHeight: '1.6', fontWeight: '400' }],
          'label-md': ['14px', { lineHeight: '1.2', letterSpacing: '0.05em', fontWeight: '500' }],
          'label-sm': ['12px', { lineHeight: '1.2', fontWeight: '500' }]
        }
      }
    }
  };
}
