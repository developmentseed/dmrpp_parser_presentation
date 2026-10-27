import { defineShikiSetup } from '@slidev/types'

// Code always sits on navy panels, so use a dark theme in both color modes
export default defineShikiSetup(() => ({
  themes: {
    dark: 'vitesse-dark',
    light: 'vitesse-dark',
  },
}))
