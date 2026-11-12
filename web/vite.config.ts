import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

/**
 * EventSim has no CORS middleware and the backend is not modified, so the browser
 * reaches it through this dev proxy at /eventsim. The proxy also attaches the bearer
 * token: client code never reads a token, so no token is inlined into the bundle.
 *
 * Token per demo role: VITE_EVENTSIM_TOKEN_<ROLE> when set, else VITE_EVENTSIM_TOKEN.
 * The client sends the role it is acting as in the X-Demo-Role header.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  const target = env.VITE_EVENTSIM_URL || 'http://127.0.0.1:8000';

  const tokenFor = (role: string | undefined): string | undefined => {
    const key = `VITE_EVENTSIM_TOKEN_${(role ?? '').toUpperCase()}`;
    return env[key] || env.VITE_EVENTSIM_TOKEN || undefined;
  };

  return {
    plugins: [react(), tailwindcss()],
    // Only these keys reach client code; tokens stay server-side in the proxy.
    envPrefix: ['VITE_USE_MOCKS'],
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/eventsim': {
          target,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/eventsim/, ''),
          configure: (proxy) => {
            proxy.on('proxyReq', (proxyReq, req) => {
              const role = req.headers['x-demo-role'];
              const token = tokenFor(Array.isArray(role) ? role[0] : role);
              proxyReq.removeHeader('x-demo-role');
              if (token) proxyReq.setHeader('Authorization', `Bearer ${token}`);
            });
          },
        },
      },
    },
  };
});
