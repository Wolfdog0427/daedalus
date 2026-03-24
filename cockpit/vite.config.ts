import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react-swc';
import path from 'node:path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const orchestratorTarget = env.VITE_ORCHESTRATOR_URL || 'http://localhost:3001';

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/daedalus': {
          target: orchestratorTarget,
          changeOrigin: true,
        },
        '/health': {
          target: orchestratorTarget,
          changeOrigin: true,
        },
      },
      fs: {
        allow: ['..'],
      },
    },
    resolve: {
      alias: {
        [path.resolve(__dirname, 'src/shared/daedalus')]: path.resolve(__dirname, '../shared/daedalus'),
      },
    },
  };
});
