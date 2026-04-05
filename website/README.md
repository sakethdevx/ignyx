# Ignyx Website

A premium Next.js marketing site for Ignyx, built with:

- Next.js
- TypeScript
- Tailwind CSS
- Framer Motion
- ShadCN-style UI primitives

## Run locally

```bash
cd website
npm install
npm run dev
```

Open `http://localhost:3000`.

## GitHub Pages deployment

The repo deploy flow is designed so:

- the Next.js marketing site is published at the root
- the MkDocs documentation is published under `/docs/`

For production builds, the workflow sets `NEXT_PUBLIC_BASE_PATH=/ignyx` so asset paths work correctly on GitHub Pages project hosting.

## Build for production

```bash
cd website
npm run build
npm run start
```

## Structure

- `app/` - Next.js app router entrypoints and global styles
- `components/landing/` - landing page sections and motion helpers
- `components/ui/` - reusable UI primitives
- `lib/` - shared utilities

## Notes

- The existing MkDocs documentation stays intact.
- This app is intended to become the premium front door for Ignyx while linking into the current docs site.
