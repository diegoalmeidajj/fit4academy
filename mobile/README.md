# Fit4Academy Mobile (Expo / React Native)

Mobile app for both **members** and **staff**. Built with Expo SDK 51 + Expo Router +
TypeScript. Talks to the Flask backend at `/api/v1/*`.

**Launch order (decided 2026-04-26)**: ship as a **PWA at `https://<domain>/app/`
first**, then publish native iOS + Android apps after the PWA validates. The same
codebase produces all three.

## Pre-requisites

You need **Node.js 18+** (or 20+) installed. macOS one-liner:

```bash
# Option A — Homebrew (recommended)
brew install node

# Option B — official installer
# Download from https://nodejs.org and run the .pkg
```

After install, verify:
```bash
node --version   # should show v18+ or v20+
npm  --version
```

## First-time setup

From the repo root:

```bash
cd mobile
npm install            # installs dependencies (~3 min on a clean machine)
```

Optionally install the Expo CLI globally for the `expo` command (otherwise use `npx expo`):
```bash
npm install -g expo-cli eas-cli
```

## Running the app

### 1. Start the backend (in another terminal)

```bash
cd /Users/diegoalmeidabusiness/Desktop/fit4academy
python3 app.py
# Backend listens on http://localhost:8080
```

### 2. Start the mobile app

```bash
cd /Users/diegoalmeidabusiness/Desktop/fit4academy/mobile
npx expo start
```

A QR code appears in the terminal:
- **iPhone**: open the Camera app, scan the QR, tap the link → opens in Expo Go
  (install [Expo Go](https://apps.apple.com/app/expo-go/id982107779) first).
- **Android**: open the Expo Go app, scan the QR.
- **Web**: press `w` in the terminal to open the browser version.
- **iOS Simulator** (macOS only): press `i` in the terminal (requires Xcode installed).

> ⚠️ If your phone is on a different network than your Mac, the app won't reach the
> backend. Either: (a) put both on the same Wi-Fi, or (b) edit `app.json` →
> `extra.apiBaseUrl` to a tunnel URL (e.g. `ngrok http 8080`).

## Test accounts (development DB)

The Flask backend seeds an admin staff account on first boot:
- **Username**: `seeds13`
- **Password**: `Seeds2026!`

For a member test login, you need to:
1. Sign in as staff via the web app (`/login`) at `http://localhost:8080`.
2. Create a member at `/members/add`.
3. Visit `/members/<id>/qr` to see the member's PIN.
4. In the mobile app, tap **"First time? Sign up with your gym PIN"** and use that PIN.

## Project layout

```
mobile/
├── app/                    # Expo Router file-based pages
│   ├── _layout.tsx         # Root layout — boots auth, gates navigation
│   ├── (auth)/             # Anonymous routes
│   │   ├── login.tsx       # member + staff login (toggle)
│   │   └── signup.tsx      # member signup with gym PIN
│   ├── (member)/index.tsx  # member home (Phase 1 will expand)
│   └── (staff)/index.tsx   # staff home (Phase 2 will expand)
├── lib/
│   ├── api.ts              # HTTP client (JWT + auto-refresh on 401)
│   ├── storage.ts          # SecureStore wrapper for tokens
│   └── theme.ts            # Brand tokens — colors, radius, spacing, fonts
├── store/
│   └── auth.ts             # Zustand store: status, me, login/logout
├── app.json                # Expo config (bundle id, permissions, plugins)
├── package.json            # Dependencies
└── tsconfig.json           # TypeScript with @/* path alias
```

## What works today (Phase 0)

- ✅ Cold start opens login screen.
- ✅ Member login (email + password) → goes to `/(member)`.
- ✅ Member sign-up with PIN → creates account and logs in.
- ✅ Staff login (username + password) → goes to `/(staff)`.
- ✅ Token refresh on 401 (transparent to UI).
- ✅ Logout clears tokens and returns to login.
- ✅ Tokens persist in iOS Keychain / Android Keystore via `expo-secure-store`.

## What's next (Phase 1) — **PWA beta**

- Build the static web bundle and serve it from the Flask backend at `/app/*`.
- Share the beta link with 3-5 partner gyms.
- Iterate on real feedback before locking down the native builds.

## Building the PWA

```bash
cd /Users/diegoalmeidabusiness/Desktop/fit4academy/mobile
npx expo export -p web
# output goes to ./dist
```

Then start the Flask backend and visit:
```
http://localhost:8080/app/
```

The Flask app already has a route (`/app/*` in `app.py`) that serves `mobile/dist`
as a single-page app. As long as `mobile/dist/index.html` exists, the PWA loads.

**Production deploy**: when `mobile/dist` is committed (or built in CI on Railway),
the same backend domain serves the PWA. No separate hosting needed.

**Install on iPhone**: open Safari → `https://<domain>/app/` → tap Share → "Add to
Home Screen". The app launches full-screen with the F4 icon.

**Install on Android**: open Chrome → `https://<domain>/app/` → menu → "Install app".

## What comes after PWA

- Member features: dashboard, payments, self-service card, receipts, push.
- Staff features: KPIs, members list, manual payment, today's classes, check-in.
- Biometric login + geofence check-in + chat + store.
- Native publish to App Store + Play Store (only after PWA validates).

See `BRAND_PLAYBOOK.md` (§11 UI components) and the plan in
`~/.claude/plans/voce-acha-melhor-desenvolver-peppy-clock.md` for the full roadmap.

## Common issues

**`Cannot find module 'expo-router/entry'`** → run `npm install` again.

**`Network request failed`** → backend isn't running, or your phone can't reach
`localhost:8080`. Use `npx expo start --tunnel` to expose via ngrok.

**`Invariant Violation: Module ... is not a registered callable module`** → clear
Metro cache: `npx expo start -c`.
