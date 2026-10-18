import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      host: '127.0.0.1',
      proxy: {
        '/v3': {
          target: 'http://127.0.0.1:8000',
          bypass: (req, res) => {
            if (res && !['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(req.socket.remoteAddress ?? '')) {
              res.statusCode = 403; res.end(); return false;
            }
          },
        },
        '/v2': {
          target: 'http://127.0.0.1:8000',
          bypass: (req, res) => {
            if (res && !['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(req.socket.remoteAddress ?? '')) {
              res.statusCode = 403;
              res.end();
              return false;
            }
          },
        },
      },
    },
  };
});
