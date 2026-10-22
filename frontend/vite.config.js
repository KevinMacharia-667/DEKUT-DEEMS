import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function pwaPrecachePlugin() {
  return {
    name: 'pwa-precache-plugin',
    apply: 'build',
    closeBundle() {
      const distDir = path.resolve(__dirname, 'dist');
      const assetsDir = path.resolve(distDir, 'assets');
      const swDistPath = path.resolve(distDir, 'sw.js');
      const swSrcPath = path.resolve(__dirname, 'public/sw.js');

      if (!fs.existsSync(swSrcPath)) return;
      let swContent = fs.readFileSync(swSrcPath, 'utf-8');

      // Discover all generated hashed JS and CSS files in dist/assets
      let hashedAssets = [];
      if (fs.existsSync(assetsDir)) {
        hashedAssets = fs
          .readdirSync(assetsDir)
          .filter((file) => !file.endsWith('.map'))
          .map((file) => `/assets/${file}`);
      }

      const buildVersion = `tukio-v${Date.now()}`;
      const precacheList = [
        '/',
        '/index.html',
        '/manifest.json',
        '/favicon.svg',
        '/favicon-32.png',
        '/apple-touch-icon.png',
        '/icon-192.png',
        '/icon-512.png',
        ...hashedAssets,
      ];

      // Update CACHE_NAME with build version
      swContent = swContent.replace(
        /const CACHE_NAME = ['"][^'"]+['"];/,
        `const CACHE_NAME = '${buildVersion}';`
      );

      // Inject full precache list including hashed Vite chunks
      swContent = swContent.replace(
        /const STATIC_PRECACHE = \[[^\]]*\];/s,
        `const STATIC_PRECACHE = ${JSON.stringify(precacheList, null, 2)};`
      );

      fs.writeFileSync(swDistPath, swContent, 'utf-8');
      console.log(`[PWA Plugin] Precached ${precacheList.length} assets into dist/sw.js (${buildVersion})`);
    },
  };
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), pwaPrecachePlugin()],
  server: {
    proxy: {
      // Forward /api requests to the FastAPI backend
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
