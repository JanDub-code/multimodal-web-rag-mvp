import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

const customTheme = {
  dark: false,
  colors: {
    primary: '#5C6BC0',
    'primary-lighten-1': '#8E99E8',
    'primary-darken-1': '#3F4FA0',
    secondary: '#7C4DFF',
    accent: '#7C4DFF',
    success: '#4CAF50',
    warning: '#FF9800',
    error: '#EF5350',
    info: '#42A5F5',
    background: '#F5F6FA',
    surface: '#FFFFFF',
    'on-background': '#1A1D2E',
    'on-surface': '#1A1D2E',
  },
}

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'customTheme',
    themes: {
      customTheme,
    },
  },
  defaults: {
    VBtn: {
      rounded: 'lg',
      variant: 'flat',
    },
    VCard: {
      rounded: 'lg',
      elevation: 0,
    },
    VTextField: {
      variant: 'outlined',
      density: 'comfortable',
    },
    VSelect: {
      variant: 'outlined',
      density: 'comfortable',
    },
    VDataTable: {
      hover: true,
    },
  },
})
