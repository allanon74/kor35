# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.

## Deploy automatico + mirror

Workflow: `.github/workflows/deploy.yml`

- Trigger automatico su push in `main`
- Trigger manuale (`workflow_dispatch`) con input `ref`
- Job `production-deploy`: build e deploy frontend su server principale
- Job `mirror-deploy`: build e deploy frontend su Raspberry mirror (`forntend_src` -> `react_build`)

Secrets principali:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`
- `DEPLOY_SSH_PORT` (opzionale, default 22)
- `REPO_PATH_ON_SERVER`
- `DEPLOY_TARGET_PATH`
- `FRONTEND_HEALTHCHECK_URL` (opzionale)

Secrets mirror:

- `MIRROR_SERVER_HOST`
- `MIRROR_SERVER_USER`
- `MIRROR_SERVER_SSH_KEY`
- `MIRROR_SERVER_SSH_PORT` (opzionale, default 22)
- `MIRROR_FRONTEND_PATH` (opzionale, default `/home/pi/kor35-replica/frontend_src`)
- `MIRROR_REACT_BUILD_PATH` (opzionale, default `/home/pi/kor35-replica/react_build`)
- `MIRROR_FRONTEND_POST_DEPLOY_COMMAND` (opzionale)
- `MIRROR_FRONTEND_HEALTHCHECK_URL` (opzionale)

### API e media: percorsi relativi (default)

Il bundle usa **`API_BASE_URL` vuoto** di default: tutte le chiamate vanno a **`/api/...`** e i media a **`/media/...`** rispetto all’host da cui apri l’app (produzione, mirror, staging). Serve che il web server / reverse proxy sul quel host inoltri `/api` e `/media` a Django e serva lo static del frontend.

- **Produzione e mirror**: non impostare `VITE_API_URL` al build (il workflow mirror fa `unset VITE_API_URL`).
- **Sviluppo locale** (`npm run dev`): `vite.config.js` fa proxy di `/api` e `/media` verso `http://127.0.0.1:8000` così i percorsi relativi funzionano senza CORS.
- **Solo eccezione**: se il frontend è servito da un host e l’API da un altro senza proxy, puoi impostare `VITE_API_URL` al build (URL assoluto del backend); non è lo schema consigliato per prod/mirror.
