import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
//   base: './', // ✅ this fixes relative paths for Chrome Extensions
  build: {
    outDir: 'build', // ✅ name matches what Chrome will load
  },
})
