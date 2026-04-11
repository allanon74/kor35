# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in this project.

## Deploy (monorepo KOR35)

Il build e il deploy non sono definiti in questa cartella: vedi il workflow **alla root del monorepo**:

- **`/.github/workflows/deploy.yml`** — build `npm` su GitHub Actions, rsync di `frontend/dist` verso `config/docker/nginx-docker/react_build`, deploy Docker produzione e mirror.

Secrets e passi: **README principale** del repository, sezione *Deploy sicuro* e *Transizione post-merge*.

**Produzione e mirror:** non impostare `VITE_API_URL` al build (il workflow fa `unset VITE_API_URL` dove serve): le chiamate restano relative a `/api/...` e `/media/...` sull’host che serve l’app.

---

## Note storiche (kor35-app separato)

In passato esisteva un workflow solo `frontend` con secret tipo `DEPLOY_HOST`, `REPO_PATH_ON_SERVER`, Apache, ecc. Con il monorepo quel flusso è **sostituito** dal file unico in root.
