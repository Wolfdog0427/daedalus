# Daedalus Node Mobile · S26 Ultra

This project is a **self-contained Daedalus mobile node** for your S26 Ultra:

- **Identity:** `node-s26-ultra-01`, labeled `S26 Ultra · Node 1`
- **Heartbeat:** periodic POST to the local presence server
- **Continuity:** last heartbeat / join / presence timestamps stored locally
- **Presence server:** lightweight Express service in `server/`
- **Join request:** explicit `/join` call from the mobile shell
- **Ready to zip and deploy**

## Layout

- `App.tsx` — Daedalus node shell UI
- `src/config/identity.ts` — canonical identity for this node
- `src/services/heartbeat.ts` — heartbeat engine
- `src/services/continuity.ts` — continuity storage (AsyncStorage)
- `src/services/presenceClient.ts` — join request + presence client
- `src/context/DaedalusContext.tsx` — wiring for identity, heartbeat, continuity, join
- `server/` — presence server (Express)

## Running on your S26 Ultra

1. Install dependencies:

   ```bash
   cd daedalus-node-mobile
   npm install
   cd server
   npm install
   ```

2. Start the presence server:

   ```bash
   npm run server
   ```

3. Start the Expo app:

   ```bash
   npm start
   ```
