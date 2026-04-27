#!/usr/bin/env python3
"""Build FIT4ACADEMY_VISION.pdf — a Phase 5 product+brand vision deck.

Renders iPhone-framed member screens and desktop-framed staff screens that
mirror the design system in mobile/lib/theme/tokens.ts and BRAND_PLAYBOOK.md.

Output: FIT4ACADEMY_VISION.pdf at the repo root. Uses Chrome headless to
generate the PDF from a self-contained HTML document.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_PATH = os.path.join(ROOT, 'FIT4ACADEMY_VISION.html')
PDF_PATH = os.path.join(ROOT, 'FIT4ACADEMY_VISION.pdf')


CSS = r"""
@page { size: Letter; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --mint: #00DC82;
  --mint-dark: #00B368;
  --mint-light: #6ee7b7;
  --cyan: #22d3ee;
  --slate-950: #0a0f1a;
  --slate-900: #0f172a;
  --slate-800: #1e293b;
  --slate-700: #475569;
  --slate-500: #64748b;
  --slate-400: #94a3b8;
  --slate-300: #cbd5e1;
  --slate-200: #e2e8f0;
  --slate-100: #f1f5f9;
  --slate-50: #f8fafc;
  --warning: #f59e0b;
  --danger: #ef4444;
}
html, body {
  font-family: 'DM Sans', -apple-system, system-ui, sans-serif;
  color: #0f172a;
  background: #fff;
}

.page {
  width: 8.5in;
  height: 11in;
  page-break-after: always;
  position: relative;
  overflow: hidden;
  break-after: page;
}
.page:last-child { page-break-after: auto; break-after: auto; }

/* — COVER — */
.cover {
  background: linear-gradient(160deg, #0f172a 0%, #0a0f1a 50%, #001a10 100%);
  color: #fff;
  padding: 1.2in 0.9in;
  display: flex;
  flex-direction: column;
}
.cover .mark {
  width: 110px; height: 110px; border-radius: 26px;
  background: linear-gradient(135deg, #00DC82, #00B368);
  display: flex; align-items: center; justify-content: center;
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 800; font-size: 44px; color: #0f172a;
  letter-spacing: -2px;
  box-shadow: 0 14px 40px rgba(0, 220, 130, 0.35);
  margin-bottom: 32px;
}
.cover h1 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 56pt; font-weight: 800; line-height: 1.0;
  letter-spacing: -2px;
  margin-bottom: 14px;
}
.cover h1 em {
  font-style: normal;
  background: linear-gradient(135deg, #6ee7b7, #22d3ee);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
}
.cover .sub {
  font-size: 13pt; color: rgba(255,255,255,0.72);
  margin-bottom: 36px;
  max-width: 5.5in; line-height: 1.5;
}
.cover .pillars {
  display: flex; gap: 18px;
  margin-top: 18px;
}
.cover .pillar {
  flex: 1;
  padding: 18px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
}
.cover .pillar h3 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 11pt; color: var(--mint-light); font-weight: 700;
  letter-spacing: 0.5px; text-transform: uppercase;
  margin-bottom: 6px;
}
.cover .pillar p { font-size: 9.5pt; color: rgba(255,255,255,0.7); line-height: 1.4; }
.cover .meta {
  margin-top: auto;
  padding-top: 18px;
  border-top: 1px solid rgba(255,255,255,0.1);
  display: flex; justify-content: space-between;
  font-size: 9pt; color: rgba(255,255,255,0.55);
}
.cover .meta strong { color: var(--mint-light); }

/* — HEADER for content pages — */
.page-header {
  display: flex; align-items: center;
  padding: 0.55in 0.7in 0.25in;
  border-bottom: 1px solid var(--slate-200);
}
.page-header .pp-mark {
  width: 28px; height: 28px; border-radius: 8px;
  background: linear-gradient(135deg, var(--mint), var(--mint-dark));
  display: flex; align-items: center; justify-content: center;
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 800; font-size: 12px; color: #0f172a;
  margin-right: 10px;
}
.page-header .pp-name {
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700; font-size: 11pt; color: var(--slate-900);
  letter-spacing: -0.3px;
}
.page-header .pp-name span { color: var(--mint-dark); }
.page-header .pp-section {
  margin-left: auto;
  font-size: 9pt; font-weight: 600;
  color: var(--slate-500);
  letter-spacing: 1px; text-transform: uppercase;
}

.page-content {
  padding: 0.3in 0.7in 0.5in;
}
.page-eyebrow {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 9pt; font-weight: 700;
  color: var(--mint-dark);
  letter-spacing: 1.5px; text-transform: uppercase;
  margin-bottom: 6px;
}
.page-title {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 28pt; font-weight: 800;
  color: var(--slate-900);
  letter-spacing: -1.2px; line-height: 1.05;
  margin-bottom: 10px;
}
.page-lede {
  font-size: 11pt; color: var(--slate-700);
  line-height: 1.5;
  max-width: 6in;
  margin-bottom: 22px;
}

/* — iPhone frame — */
.phone {
  width: 280px; height: 580px;
  background: #0a0f1a;
  border-radius: 44px;
  padding: 8px;
  position: relative;
  box-shadow:
    0 0 0 2px #1f2937,
    0 30px 60px rgba(0,0,0,0.18),
    0 12px 24px rgba(0,0,0,0.10);
}
.phone .screen {
  width: 100%; height: 100%;
  border-radius: 36px;
  overflow: hidden;
  position: relative;
  background: #000;
}
.phone .notch {
  position: absolute;
  top: 14px; left: 50%;
  transform: translateX(-50%);
  width: 90px; height: 22px;
  background: #0a0f1a;
  border-radius: 14px;
  z-index: 10;
}
.phone .status-bar {
  position: absolute; top: 0; left: 0; right: 0;
  height: 36px; padding: 12px 24px 0;
  display: flex; justify-content: space-between; align-items: center;
  font-family: 'SF Pro Text', -apple-system, system-ui, sans-serif;
  font-size: 9pt; font-weight: 600;
  color: var(--text-color, #fff);
  z-index: 5;
}
.phone .home-indicator {
  position: absolute; bottom: 5px; left: 50%;
  transform: translateX(-50%);
  width: 100px; height: 4px;
  background: rgba(255,255,255,0.45);
  border-radius: 2px; z-index: 10;
}

/* iPhone screen content — light mode default */
.phone-content {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  padding: 38px 14px 18px;
  background: #fff;
  font-family: -apple-system, system-ui, sans-serif;
  font-size: 9pt;
  color: #0f172a;
  overflow: hidden;
}
.phone-content.dark { background: #000; color: #fff; }

/* — Mocked tab bar — */
.tab-bar {
  position: absolute; bottom: 0; left: 0; right: 0;
  height: 56px;
  border-top: 0.5px solid rgba(0,0,0,0.06);
  background: #fff;
  display: flex;
  padding: 8px 0 14px;
  z-index: 5;
}
.tab-bar.dark { background: #111113; border-top-color: rgba(255,255,255,0.08); }
.tab { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 3px; }
.tab svg { width: 18px; height: 18px; stroke: #94a3b8; fill: none; stroke-width: 1.5; }
.tab.active svg { stroke: var(--mint); }
.tab-label { font-size: 7.5pt; font-weight: 600; color: #94a3b8; }
.tab.active .tab-label { color: var(--mint-dark); }

/* — Greeting — */
.h-greet {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 12px;
}
.avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: linear-gradient(135deg, var(--mint), var(--mint-dark));
  color: #0f172a; font-family: 'Space Grotesk'; font-weight: 800; font-size: 10pt;
  display: flex; align-items: center; justify-content: center;
}
.h-greet-text { flex: 1; }
.h-greet-text .small { font-size: 7pt; color: var(--slate-500); font-weight: 500; }
.h-greet-text .name { font-size: 11pt; font-weight: 700; letter-spacing: -0.3px; }
.bell {
  width: 28px; height: 28px; border-radius: 14px;
  background: var(--slate-100);
  display: flex; align-items: center; justify-content: center;
  position: relative;
}
.bell-dot { position: absolute; top: 4px; right: 4px; width: 7px; height: 7px; border-radius: 50%; background: var(--warning); border: 1.5px solid #fff; }

/* — Hero rank card — */
.rank-card {
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 16px;
  padding: 14px;
  margin-bottom: 10px;
  background: #fff;
  box-shadow: 0 4px 16px rgba(0,0,0,0.04);
}
.rank-card .row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.rank-card .eyebrow { font-size: 7pt; font-weight: 700; color: var(--slate-500); letter-spacing: 1px; }
.rank-card .badge-active {
  background: rgba(0,220,130,0.10);
  color: var(--mint-dark);
  padding: 2px 8px; border-radius: 999px;
  font-size: 6.5pt; font-weight: 700;
}
.rank-card h2 {
  font-family: 'Space Grotesk'; font-size: 17pt; font-weight: 800;
  letter-spacing: -0.6px; margin: 4px 0 1px;
}
.rank-card h2 small { color: var(--slate-500); font-weight: 500; }
.rank-card .meta { font-size: 7.5pt; color: var(--slate-500); margin-bottom: 8px; }
.belt {
  height: 24px; border-radius: 5px;
  display: flex; overflow: hidden;
  box-shadow: 0 4px 10px rgba(0,0,0,0.10);
}
.belt .body { flex: 1; }
.belt .tape {
  width: 38px; background: #0f1419;
  display: flex; align-items: center; gap: 3px;
  padding-left: 5px;
}
.belt .stripe {
  width: 2px; height: 16px; background: rgba(255,255,255,0.10);
  border-radius: 1px;
}
.belt .stripe.on { background: #fff; }

/* — Stats — */
.stats { display: flex; gap: 8px; margin-bottom: 10px; }
.stat-card {
  flex: 1; padding: 10px; border-radius: 14px;
  border: 1px solid rgba(0,0,0,0.06);
}
.stat-card.accent {
  background: rgba(0,220,130,0.06);
}
.stat-card .head { font-size: 6.5pt; font-weight: 700; color: var(--mint-dark); letter-spacing: 0.6px; }
.stat-card.neutral .head { color: var(--slate-500); }
.stat-card .big {
  font-family: 'Space Grotesk'; font-size: 18pt; font-weight: 800;
  letter-spacing: -1px; margin-top: 2px;
}
.stat-card .lab { font-size: 7pt; color: var(--slate-500); margin-top: 1px; }

/* — Quick action list — */
.qa-card {
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 14px;
  background: #fff;
  overflow: hidden;
  margin-top: 6px;
}
.qa-row {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 11px;
  border-top: 0.5px solid rgba(0,0,0,0.05);
}
.qa-row:first-child { border-top: 0; }
.qa-icon-tile {
  width: 28px; height: 28px; border-radius: 8px;
  background: var(--slate-100);
  display: flex; align-items: center; justify-content: center;
}
.qa-icon-tile.accent { background: rgba(0,220,130,0.10); }
.qa-icon-tile svg { width: 14px; height: 14px; stroke: var(--slate-700); fill: none; stroke-width: 1.5; }
.qa-icon-tile.accent svg { stroke: var(--mint-dark); }
.qa-text { flex: 1; }
.qa-text .l1 { font-size: 8.5pt; font-weight: 600; }
.qa-text .l2 { font-size: 7pt; color: var(--slate-500); margin-top: 0.5px; }
.qa-badge {
  background: var(--warning); color: #0f172a;
  font-weight: 800; font-size: 7.5pt;
  border-radius: 9px; min-width: 16px; padding: 2px 5px;
  text-align: center;
  margin-right: 4px;
  box-shadow: 0 2px 6px rgba(245,158,11,0.4);
}
.qa-chev svg { width: 12px; height: 12px; stroke: var(--slate-300); fill: none; stroke-width: 1.5; }

/* — Section eyebrow — */
.s-eyebrow {
  font-size: 7pt; font-weight: 700; color: var(--slate-500);
  letter-spacing: 1.2px; margin: 12px 0 6px;
}

/* — Unread alert (orange) — */
.alert-unread {
  display: flex; align-items: center; gap: 9px;
  padding: 10px;
  background: rgba(245,158,11,0.08);
  border: 1px solid rgba(245,158,11,0.45);
  border-radius: 12px;
  margin-bottom: 10px;
}
.alert-unread .dot {
  width: 30px; height: 30px; border-radius: 15px; background: var(--warning);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 10px rgba(245,158,11,0.4);
}
.alert-unread .dot svg { width: 13px; height: 13px; stroke: #0f172a; fill: none; stroke-width: 1.5; }
.alert-unread .body { flex: 1; }
.alert-unread .head { font-size: 7pt; font-weight: 700; color: var(--warning); letter-spacing: 0.5px; }
.alert-unread .preview { font-size: 8pt; margin-top: 1px; }

/* — Login screen — */
.login-mock {
  padding: 26px 20px 16px;
  text-align: center;
  height: 100%;
  display: flex; flex-direction: column;
  background: #fff;
}
.login-mock .login-mark {
  width: 56px; height: 56px; border-radius: 16px;
  background: linear-gradient(135deg, var(--mint), var(--mint-dark));
  display: flex; align-items: center; justify-content: center;
  font-family: 'Space Grotesk'; font-weight: 800; font-size: 22px;
  color: #0f172a; letter-spacing: -1.2px;
  margin: 6px auto 16px;
  box-shadow: 0 12px 28px rgba(0,220,130,0.30);
}
.login-mock h1 {
  font-family: 'Space Grotesk'; font-size: 22pt; font-weight: 800;
  letter-spacing: -0.8px;
}
.login-mock h1 span { color: var(--mint); }
.login-mock .tag { font-size: 8pt; color: var(--slate-500); margin: 5px 0 18px; }
.seg {
  display: flex; gap: 3px; padding: 3px;
  background: var(--slate-100);
  border-radius: 10px;
  margin-bottom: 14px;
}
.seg .opt {
  flex: 1; padding: 7px;
  border-radius: 7px;
  text-align: center;
  font-size: 8.5pt; font-weight: 700; color: var(--slate-500);
}
.seg .opt.active {
  background: #fff; color: #0f172a;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.field { text-align: left; margin-bottom: 9px; }
.field-label { font-size: 7pt; font-weight: 600; color: var(--slate-700); margin-bottom: 3px; }
.field-input {
  border: 1.5px solid rgba(0,0,0,0.08);
  border-radius: 10px;
  padding: 9px 11px;
  font-size: 8.5pt;
  color: var(--slate-400);
}
.field.focused .field-input { border-color: var(--mint); box-shadow: 0 0 0 3px rgba(0,220,130,0.10); }
.btn-primary {
  background: linear-gradient(135deg, var(--mint), var(--mint-dark));
  color: #0f172a;
  font-weight: 800; font-size: 9pt; letter-spacing: 0.2px;
  padding: 10px;
  border-radius: 12px;
  text-align: center;
  margin-top: 6px;
  box-shadow: 0 4px 14px rgba(0,220,130,0.30);
}
.signup-link { font-size: 7pt; color: var(--slate-500); margin-top: 12px; }
.signup-link strong { color: var(--mint-dark); font-weight: 700; }
.trust { font-size: 6.5pt; color: var(--slate-400); margin-top: auto; padding-top: 8px; }

/* — Check-in in-range hero — */
.checkin-hero {
  border-radius: 20px;
  background: var(--mint);
  padding: 18px;
  text-align: center;
  margin-bottom: 10px;
  box-shadow: 0 16px 32px rgba(0,220,130,0.30);
}
.checkin-hero .pin-icon {
  width: 44px; height: 44px; border-radius: 22px;
  background: rgba(15,23,42,0.15);
  display: inline-flex; align-items: center; justify-content: center;
  margin-bottom: 8px;
}
.checkin-hero .pin-icon svg { width: 22px; height: 22px; stroke: #0f172a; fill: none; stroke-width: 1.5; }
.checkin-hero .eyebrow {
  font-size: 7pt; font-weight: 700; color: rgba(15,23,42,0.7); letter-spacing: 1.2px;
}
.checkin-hero h2 {
  font-family: 'Space Grotesk';
  font-size: 16pt; font-weight: 800;
  color: #0f172a; letter-spacing: -0.8px;
  margin: 4px 0 2px;
}
.checkin-hero .meters { font-size: 7.5pt; color: rgba(15,23,42,0.7); }
.checkin-hero .pill {
  background: #0f172a; color: #fff;
  font-weight: 800; font-size: 9pt;
  padding: 10px 22px;
  border-radius: 999px;
  display: inline-flex; align-items: center; gap: 6px;
  margin-top: 12px;
}
.checkin-hero .pill svg { width: 12px; height: 12px; stroke: #fff; fill: none; stroke-width: 2; }

/* — Faceid sheet (Phase 5 native overlay) — */
.faceid-sheet {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(15,23,42,0.92);
  backdrop-filter: blur(8px);
  display: flex; flex-direction: column;
  justify-content: center; align-items: center;
  border-radius: 36px;
  z-index: 20;
  color: #fff;
}
.faceid-sheet .face-icon {
  width: 64px; height: 64px; border-radius: 14px;
  border: 2px solid #fff; display: inline-flex;
  align-items: center; justify-content: center; margin-bottom: 14px;
}
.faceid-sheet .face-icon svg { width: 30px; height: 30px; stroke: #fff; fill: none; stroke-width: 2; }
.faceid-sheet .face-tag { font-size: 8pt; color: rgba(255,255,255,0.65); }
.faceid-sheet .face-h { font-size: 13pt; font-weight: 700; margin-top: 4px; }
.faceid-sheet .face-cap { font-size: 7pt; color: rgba(255,255,255,0.5); margin-top: 8px; }

/* — Lock screen / push notification mock — */
.lock-screen {
  background: linear-gradient(160deg, #1f2937, #111827 60%, #0a0f1a);
  color: #fff;
  height: 100%;
  padding: 40px 14px 18px;
  position: relative;
}
.lock-time {
  font-family: 'SF Pro Display', -apple-system, sans-serif;
  font-weight: 200;
  font-size: 56pt;
  text-align: center;
  margin: 14px 0 4px;
  letter-spacing: -3px;
}
.lock-date { font-size: 10pt; text-align: center; color: rgba(255,255,255,0.7); margin-bottom: 18px; }
.lock-notif {
  background: rgba(255,255,255,0.10);
  backdrop-filter: blur(10px);
  border-radius: 14px;
  padding: 10px 12px;
  display: flex; gap: 9px;
  margin-bottom: 8px;
}
.lock-notif .icon-square {
  width: 26px; height: 26px; border-radius: 7px;
  background: linear-gradient(135deg, var(--mint), var(--mint-dark));
  display: flex; align-items: center; justify-content: center;
  font-family: 'Space Grotesk'; font-weight: 800; font-size: 10pt;
  color: #0f172a; letter-spacing: -1px;
  flex-shrink: 0;
}
.lock-notif .body { flex: 1; }
.lock-notif .title { font-size: 8pt; font-weight: 700; }
.lock-notif .text { font-size: 7.5pt; color: rgba(255,255,255,0.85); margin-top: 1px; }
.lock-notif .time-stamp { font-size: 7pt; color: rgba(255,255,255,0.5); }

/* — Live activity (Phase 5) — */
.live-activity {
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(20px);
  border-radius: 22px;
  padding: 12px 14px;
  display: flex; align-items: center; gap: 10px;
  border: 0.5px solid rgba(255,255,255,0.10);
}
.live-activity .lv-mark {
  width: 26px; height: 26px; border-radius: 8px;
  background: linear-gradient(135deg, var(--mint), var(--mint-dark));
  font-family: 'Space Grotesk'; font-weight: 800; font-size: 9pt;
  color: #0f172a; display: flex; align-items: center; justify-content: center;
}
.live-activity .body { flex: 1; }
.live-activity .lv-eye { font-size: 6.5pt; color: rgba(255,255,255,0.6); letter-spacing: 0.6px; }
.live-activity .lv-l1 { font-size: 8pt; font-weight: 700; }
.live-activity .lv-l2 { font-size: 7pt; color: rgba(255,255,255,0.7); margin-top: 1px; }
.live-activity .lv-time {
  background: var(--mint); color: #0f172a;
  font-weight: 800; font-size: 9pt;
  padding: 5px 9px; border-radius: 7px;
}

/* — Chat bubbles — */
.chat-bg { background: var(--slate-50); height: 100%; padding: 38px 12px 60px; overflow: hidden; }
.chat-head { padding: 4px 0 10px; border-bottom: 0.5px solid rgba(0,0,0,0.06); margin-bottom: 12px; }
.chat-head .chat-name { font-size: 11pt; font-weight: 700; }
.chat-head .chat-sub { font-size: 7.5pt; color: var(--slate-500); }
.bubble {
  max-width: 78%;
  padding: 7px 11px;
  border-radius: 14px;
  margin-bottom: 6px;
  font-size: 8.5pt; line-height: 1.35;
}
.bubble.coach { background: #fff; align-self: flex-start; border: 0.5px solid rgba(0,0,0,0.05); }
.bubble.mine { background: var(--mint); color: #0f172a; align-self: flex-end; margin-left: auto; }
.bubble-time { font-size: 6pt; color: var(--slate-400); margin-top: 1px; text-align: right; }

/* — Payment screen with Stripe — */
.pay-amount {
  text-align: center; padding: 18px;
}
.pay-amount .lab { font-size: 7pt; font-weight: 700; color: var(--slate-500); letter-spacing: 0.6px; }
.pay-amount .big {
  font-family: 'Space Grotesk'; font-size: 32pt; font-weight: 800;
  color: var(--mint-dark); letter-spacing: -1.5px; margin-top: 2px;
}
.pay-amount .fee { font-size: 7pt; color: var(--slate-500); }
.stripe-mock {
  border: 1.5px solid var(--slate-200);
  border-radius: 12px;
  background: #fff;
  margin-bottom: 8px;
  padding: 8px 10px;
  font-size: 8pt;
}
.stripe-mock .pm-tabs { display: flex; gap: 6px; margin-bottom: 8px; }
.stripe-mock .pm-tab {
  flex: 1; padding: 6px;
  background: var(--slate-50); border: 1px solid var(--slate-200);
  border-radius: 8px; text-align: center;
  font-size: 7pt; font-weight: 600; color: var(--slate-500);
}
.stripe-mock .pm-tab.active { background: rgba(0,220,130,0.06); border-color: var(--mint); color: var(--mint-dark); }
.stripe-mock .input-line {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 0; border-bottom: 1px solid var(--slate-100);
}
.stripe-mock .input-line:last-child { border-bottom: 0; }
.stripe-mock .ph { color: var(--slate-400); font-size: 7.5pt; }
.applepay-btn {
  background: #000; color: #fff;
  padding: 10px;
  text-align: center;
  border-radius: 10px;
  font-size: 9pt; font-weight: 700;
  margin-top: 6px;
}

/* — Desktop frame — */
.desktop {
  width: 100%;
  height: 4.6in;
  background: #fff;
  border-radius: 8px;
  box-shadow:
    0 0 0 1px rgba(0,0,0,0.05),
    0 24px 48px rgba(0,0,0,0.10),
    0 8px 16px rgba(0,0,0,0.06);
  overflow: hidden;
  display: flex;
}
.desktop-bar {
  position: relative;
  background: #f8fafc;
  border-bottom: 1px solid var(--slate-200);
  height: 26px;
  padding: 0 12px;
  display: flex; align-items: center;
}
.desktop-bar .dots { display: flex; gap: 5px; }
.desktop-bar .dot { width: 9px; height: 9px; border-radius: 50%; background: #e2e8f0; }
.desktop-bar .dots .red { background: #ef4444; }
.desktop-bar .dots .yel { background: #f59e0b; }
.desktop-bar .dots .grn { background: #10b981; }
.desktop-bar .url {
  margin-left: 16px;
  font-size: 7pt; color: var(--slate-500);
  font-family: monospace;
}
.staff-app { flex: 1; display: flex; }
.sidebar {
  width: 130px; background: #0f172a; color: #fff;
  padding: 12px 8px;
}
.sidebar .brand { display: flex; align-items: center; gap: 6px; padding: 4px 6px 12px; }
.sidebar .brand .sb-mark {
  width: 22px; height: 22px; border-radius: 6px;
  background: linear-gradient(135deg, var(--mint), var(--mint-dark));
  display: flex; align-items: center; justify-content: center;
  font-family: 'Space Grotesk'; font-weight: 800; font-size: 9pt; color: #0f172a;
}
.sidebar .brand .sb-name { font-family: 'Space Grotesk'; font-weight: 700; font-size: 10pt; }
.sb-section-label { font-size: 6.5pt; font-weight: 700; color: rgba(255,255,255,0.4); letter-spacing: 1px; margin: 10px 0 5px; padding: 0 6px; }
.sb-link {
  display: flex; align-items: center; gap: 7px;
  padding: 6px 8px; border-radius: 6px;
  font-size: 8pt; color: rgba(255,255,255,0.65);
  margin-bottom: 1px;
  position: relative;
}
.sb-link.active { background: rgba(0,220,130,0.12); color: var(--mint); }
.sb-link svg { width: 11px; height: 11px; stroke: currentColor; fill: none; stroke-width: 1.5; }
.sb-pill {
  margin-left: auto;
  background: rgba(245,158,11,0.22);
  color: var(--warning);
  border: 1px solid rgba(245,158,11,0.4);
  font-size: 6pt; font-weight: 700;
  padding: 1px 6px; border-radius: 999px;
}
.staff-main {
  flex: 1; padding: 14px 18px;
  background: #f8fafc;
  overflow: hidden;
}
.staff-h1 {
  font-family: 'Space Grotesk'; font-size: 16pt; font-weight: 800;
  letter-spacing: -0.6px; color: var(--slate-900);
  margin-bottom: 12px;
}
.kpi-row { display: flex; gap: 8px; margin-bottom: 10px; }
.kpi {
  flex: 1; background: #fff;
  border: 1px solid var(--slate-200);
  border-radius: 8px;
  padding: 8px 10px;
}
.kpi .lab { font-size: 6.5pt; color: var(--slate-500); font-weight: 600; }
.kpi .num { font-family: 'Space Grotesk'; font-size: 13pt; font-weight: 800; letter-spacing: -0.5px; color: var(--slate-900); }
.kpi .delta { font-size: 6.5pt; color: var(--mint-dark); font-weight: 600; }

.banner-orange {
  border-radius: 10px;
  padding: 10px 12px;
  background: linear-gradient(135deg, rgba(245,158,11,0.12), rgba(249,115,22,0.06));
  border: 1px solid rgba(245,158,11,0.30);
  display: flex; align-items: center; gap: 9px;
  margin-bottom: 8px;
}
.banner-orange .icn {
  width: 26px; height: 26px; border-radius: 8px;
  background: rgba(245,158,11,0.20);
  display: flex; align-items: center; justify-content: center;
}
.banner-orange .icn svg { width: 13px; height: 13px; stroke: var(--warning); fill: none; stroke-width: 1.5; }
.banner-orange .h { font-size: 8pt; font-weight: 700; }
.banner-orange .h-sub { font-size: 6.5pt; color: var(--slate-500); }
.banner-thread {
  background: #fff; border: 1px solid var(--slate-200);
  border-left: 3px solid var(--warning);
  border-radius: 7px;
  padding: 6px 10px;
  display: flex; align-items: center; gap: 7px;
  margin-bottom: 4px;
}
.banner-thread .av-circle {
  width: 22px; height: 22px; border-radius: 50%;
  background: rgba(245,158,11,0.20); color: var(--warning);
  font-weight: 700; font-size: 7pt;
  display: flex; align-items: center; justify-content: center;
}
.banner-thread .body .name { font-size: 8pt; font-weight: 700; }
.banner-thread .body .preview { font-size: 7pt; color: var(--slate-500); margin-top: 1px; }

/* — Page rows for layouts — */
.row-2 { display: flex; gap: 18px; align-items: flex-start; }
.col { flex: 1; }
.col p { font-size: 9.5pt; color: var(--slate-700); line-height: 1.55; margin-bottom: 8px; }

/* — Color swatches — */
.swatches {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
  margin-bottom: 10px;
}
.sw { border-radius: 8px; padding: 10px; color: #fff; }
.sw .h { font-family: 'Space Grotesk'; font-weight: 700; font-size: 9pt; letter-spacing: -0.3px; }
.sw .hex { font-family: monospace; font-size: 7pt; opacity: 0.8; margin-top: 1px; }

/* — Type spec — */
.type-spec { display: flex; gap: 10px; margin-bottom: 8px; align-items: baseline; }
.type-spec .lbl { font-family: 'Space Grotesk'; font-weight: 700; font-size: 8pt; color: var(--slate-500); width: 60pt; letter-spacing: 0.4px; }
.type-spec .sample { color: var(--slate-900); }

/* — Roadmap — */
.roadmap { display: flex; gap: 10px; margin-top: 10px; }
.phase {
  flex: 1; padding: 12px;
  border: 1px solid var(--slate-200);
  border-radius: 12px;
  background: #fff;
  position: relative;
}
.phase.done { background: rgba(0,220,130,0.06); border-color: rgba(0,220,130,0.30); }
.phase.now { background: rgba(34,211,238,0.06); border-color: rgba(34,211,238,0.40); }
.phase.future { opacity: 0.85; }
.phase .num {
  font-family: 'Space Grotesk'; font-size: 18pt; font-weight: 800;
  color: var(--slate-300); letter-spacing: -1px;
}
.phase.done .num, .phase.now .num { color: var(--mint-dark); }
.phase .nm { font-size: 9pt; font-weight: 700; margin: 2px 0 4px; }
.phase .ds { font-size: 7.5pt; color: var(--slate-500); line-height: 1.4; }
.phase .stat-pill {
  position: absolute; top: 10px; right: 10px;
  font-size: 6pt; font-weight: 700; letter-spacing: 0.4px;
  padding: 2px 6px; border-radius: 999px;
  background: var(--slate-100); color: var(--slate-500);
  text-transform: uppercase;
}
.phase.done .stat-pill { background: rgba(0,220,130,0.12); color: var(--mint-dark); }
.phase.now .stat-pill { background: rgba(34,211,238,0.10); color: #0891b2; }

/* — Footer — */
.footer-mark {
  position: absolute; bottom: 0.35in; left: 0.7in; right: 0.7in;
  display: flex; align-items: center; justify-content: space-between;
  font-size: 8pt; color: var(--slate-400);
}
.footer-mark .ftr-mark {
  width: 18px; height: 18px; border-radius: 5px;
  background: linear-gradient(135deg, var(--mint), var(--mint-dark));
  font-family: 'Space Grotesk'; font-weight: 800; font-size: 7pt;
  color: #0f172a; display: inline-flex; align-items: center; justify-content: center;
  margin-right: 5px; vertical-align: middle;
}

.layout-screens {
  display: flex; gap: 12px; justify-content: center;
  margin-top: 10px;
}
.screen-caption {
  text-align: center;
  font-size: 8pt; color: var(--slate-500);
  margin-top: 6px; max-width: 280px;
}
.screen-caption strong { color: var(--slate-900); font-weight: 700; }

/* — Final CTA page — */
.cta-page {
  background: #0f172a;
  color: #fff;
  padding: 1in 0.9in;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.cta-page h1 {
  font-family: 'Space Grotesk'; font-size: 36pt; font-weight: 800;
  letter-spacing: -1.5px; line-height: 1.05;
}
.cta-page h1 em {
  font-style: normal;
  background: linear-gradient(135deg, var(--mint-light), var(--cyan));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.cta-page .cta-sub { font-size: 14pt; color: rgba(255,255,255,0.7); margin-top: 16px; max-width: 6in; line-height: 1.45; }
.cta-page .cta-row { margin-top: 30px; display: flex; gap: 16px; flex-wrap: wrap; }
.cta-page .cta-pill {
  padding: 10px 18px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.20);
  font-size: 10pt; color: rgba(255,255,255,0.85);
}
.cta-page .cta-pill.solid {
  background: linear-gradient(135deg, var(--mint), var(--mint-dark));
  color: #0f172a; font-weight: 700;
  border: none;
}

"""


# ────────────────────────────────────────────────────────────────────
#  Reusable SVG icons — minimal, stroke 1.5
# ────────────────────────────────────────────────────────────────────

def icon(name, size=14):
    paths = {
        'home':    '<path d="M3 11l9-7 9 7M5 9.5V20a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V9.5" />',
        'cal':     '<path d="M4 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7Z M8 3v4M16 3v4M4 10h16" />',
        'pin':     '<path d="M12 21s7-5.5 7-11a7 7 0 1 0-14 0c0 5.5 7 11 7 11Z" /><circle cx="12" cy="10" r="2.5" />',
        'msg':     '<path d="M21 12c0 4.4-4 8-9 8a9.7 9.7 0 0 1-3.5-.65L4 21l1.5-3.5A7.5 7.5 0 0 1 3 12c0-4.4 4-8 9-8s9 3.6 9 8Z" />',
        'person':  '<circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 3.5-7 8-7s8 3 8 7" />',
        'card':    '<path d="M2 7a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7Z" /><path d="M2 10h20" />',
        'belt':    '<path d="M3 12h18M3 12l3-4M3 12l3 4M21 12l-3-4M21 12l-3 4M9 8v8M15 8v8" />',
        'check':   '<path d="M5 12l4.5 4.5L19 7" />',
        'chev':    '<path d="M9 6l6 6-6 6" />',
        'bell':    '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.94 1.94 0 0 0 3.4 0" />',
        'face':    '<path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2" /><circle cx="9" cy="11" r="0.6" fill="currentColor"/><circle cx="15" cy="11" r="0.6" fill="currentColor"/><path d="M9 16c1 1 2 1.5 3 1.5s2-.5 3-1.5" />',
        'lock':    '<path d="M5 11h14v9a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-9Z" /><path d="M8 11V7a4 4 0 0 1 8 0v4" />',
        'trophy':  '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4ZM7 6H4v2a3 3 0 0 0 3 3M17 6h3v2a3 3 0 0 1-3 3" />',
        'send':    '<path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7Z" />',
        'shop':    '<path d="M5 7h14l-1.5 12a2 2 0 0 1-2 1.7H8.5a2 2 0 0 1-2-1.7L5 7Z M9 7V5a3 3 0 0 1 6 0v2" />',
        'plus':    '<path d="M12 5v14M5 12h14" />',
        'logout':  '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />',
        'gear':    '<path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.6 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.6-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />',
        'graph':   '<path d="M3 3v18h18 M7 14l3-3 3 3 5-5" />',
        'users':   '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M23 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75" />',
    }
    p = paths.get(name, '')
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{p}</svg>'


# ────────────────────────────────────────────────────────────────────
#  Page builders
# ────────────────────────────────────────────────────────────────────

def page_header(section):
    return f"""
    <div class="page-header">
      <div class="pp-mark">F4</div>
      <div class="pp-name">Fit4<span>Academy</span></div>
      <div class="pp-section">{section}</div>
    </div>
    """

def footer(num, total):
    return f"""
    <div class="footer-mark">
      <div><span class="ftr-mark">F4</span><span style="color:#94a3b8;">Phase 5 product vision · Confidential</span></div>
      <div>{num} / {total}</div>
    </div>
    """

def cover():
    return """
    <div class="page cover">
      <div class="mark">F4</div>
      <h1>The <em>full</em> picture.</h1>
      <div class="sub">A walk-through of Fit4Academy at Phase 5 — the native iOS &amp; Android product, plus the SaaS your gym owners use to run everything.</div>
      <div class="pillars">
        <div class="pillar">
          <h3>For owners</h3>
          <p>Run the front desk, payments, classes, members, and message threads — all in one screen.</p>
        </div>
        <div class="pillar">
          <h3>For students</h3>
          <p>Check in by walking up to the gym, pay, message your coach, track your belt — all in one app.</p>
        </div>
        <div class="pillar">
          <h3>For the brand</h3>
          <p>Mint Green and Slate, Space Grotesk for headlines, DM Sans for everything else.</p>
        </div>
      </div>
      <div class="meta">
        <div><strong>Fit4Academy</strong><br><span style="font-size:8pt;">Run your academy. Not your spreadsheets.</span></div>
        <div style="text-align:right;">PRODUCT VISION · v1<br>2026-04-27</div>
      </div>
    </div>
    """

def brand_page(num, total):
    return f"""
    <div class="page">
      {page_header('01 — Brand essentials')}
      <div class="page-content">
        <div class="page-eyebrow">BRAND ESSENTIALS</div>
        <div class="page-title">A precise, calm, premium brand.</div>
        <div class="page-lede">Fit4Academy speaks softly and shows up sharply. Mint Green for action and confirmation, Slate for everything else, Space Grotesk for numbers that should feel proud, DM Sans for the words that stay out of the way.</div>

        <h4 style="font-family:'Space Grotesk';font-weight:700;font-size:9pt;color:#475569;letter-spacing:0.5px;text-transform:uppercase;margin-bottom:8px;">Primary palette</h4>
        <div class="swatches">
          <div class="sw" style="background:#00DC82;color:#0f172a;"><div class="h">Mint Green</div><div class="hex">#00DC82</div></div>
          <div class="sw" style="background:#00B368;"><div class="h">Mint Dark</div><div class="hex">#00B368</div></div>
          <div class="sw" style="background:#0f172a;"><div class="h">Slate 900</div><div class="hex">#0f172a</div></div>
          <div class="sw" style="background:#22d3ee;color:#0f172a;"><div class="h">Cyan Accent</div><div class="hex">#22d3ee</div></div>
        </div>

        <h4 style="font-family:'Space Grotesk';font-weight:700;font-size:9pt;color:#475569;letter-spacing:0.5px;text-transform:uppercase;margin:18px 0 8px;">Typography</h4>
        <div class="type-spec">
          <div class="lbl">DISPLAY</div>
          <div class="sample" style="font-family:'Space Grotesk';font-weight:800;font-size:30pt;letter-spacing:-1.5px;line-height:1;">Train. <span style="background:linear-gradient(135deg,#6ee7b7,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">Track.</span> Get better.</div>
        </div>
        <div class="type-spec">
          <div class="lbl">H1</div>
          <div class="sample" style="font-family:'Space Grotesk';font-weight:700;font-size:18pt;letter-spacing:-0.5px;">Run your academy. Not your spreadsheets.</div>
        </div>
        <div class="type-spec">
          <div class="lbl">BODY</div>
          <div class="sample" style="font-family:'DM Sans';font-size:11pt;line-height:1.5;color:#334155;">For paragraphs, labels, and forms. Avoids drama. Reads on a phone in 4G.</div>
        </div>
        <div class="type-spec">
          <div class="lbl">NUMBERS</div>
          <div class="sample" style="font-family:'Space Grotesk';font-weight:800;font-size:30pt;color:#0f172a;letter-spacing:-1.5px;">$12,480 · 248 members · 19 today</div>
        </div>

        <h4 style="font-family:'Space Grotesk';font-weight:700;font-size:9pt;color:#475569;letter-spacing:0.5px;text-transform:uppercase;margin:18px 0 8px;">Voice</h4>
        <div class="row-2">
          <div class="col">
            <p style="font-size:9.5pt;color:#334155;line-height:1.5;"><strong>What we sound like.</strong> Direct. Specific. Quietly confident. We talk to gym owners like a peer who's been on the mats — not a marketer.</p>
          </div>
          <div class="col">
            <p style="font-size:9.5pt;color:#334155;line-height:1.5;"><strong>What we don't.</strong> No "supercharge", no "revolutionary", no "10x". No exclamation marks unless they're earned.</p>
          </div>
        </div>
      </div>
      {footer(num, total)}
    </div>
    """

def member_overview(num, total):
    return f"""
    <div class="page">
      {page_header('02 — The member side')}
      <div class="page-content">
        <div class="page-eyebrow">FOR STUDENTS</div>
        <div class="page-title">An app that knows when they arrive at the gym.</div>
        <div class="page-lede">Members open the app once, sign up with the gym's PIN, and from then on every interaction is one tap or one face-scan: walk up to the door and check in, see today's class, message the coach, pay the monthly with Apple Pay. Native iOS and Android in Phase 5 unlock the proximity push, biometric confirmation, and Live Activities below.</div>

        <div class="layout-screens">
          <div>
            {iphone_login()}
            <div class="screen-caption"><strong>Sign in</strong><br>Member &amp; staff modes share a single screen. The first-time sign-up uses the per-member PIN that staff hands out.</div>
          </div>
          <div>
            {iphone_home()}
            <div class="screen-caption"><strong>Home</strong><br>Time-aware greeting, real belt graphic with stripes, the unread coach-message banner if any, and the four most-used actions one tap away.</div>
          </div>
        </div>
      </div>
      {footer(num, total)}
    </div>
    """

def iphone_login():
    return """
    <div class="phone">
      <div class="screen">
        <div class="notch"></div>
        <div class="status-bar"><span>9:41</span><span>·· ·· 100%</span></div>
        <div class="phone-content">
          <div class="login-mock">
            <div class="login-mark">F4</div>
            <h1>Fit4<span>Academy</span></h1>
            <div class="tag">Train. Track. Get better.</div>

            <div class="seg">
              <div class="opt active">Member</div>
              <div class="opt">Staff</div>
            </div>

            <div class="field focused">
              <div class="field-label">Email</div>
              <div class="field-input">you@email.com</div>
            </div>
            <div class="field">
              <div class="field-label">Password</div>
              <div class="field-input">••••••••</div>
            </div>
            <div class="btn-primary">Sign in</div>
            <div class="signup-link">First time? <strong>Sign up with your gym PIN</strong></div>
            <div class="trust">🔒 Secured by 256-bit encryption</div>
          </div>
        </div>
      </div>
    </div>
    """

def iphone_home():
    return f"""
    <div class="phone">
      <div class="screen">
        <div class="notch"></div>
        <div class="status-bar" style="--text-color:#0f172a;color:#0f172a;"><span>9:41</span><span>·· ·· 100%</span></div>
        <div class="phone-content">
          <div class="h-greet">
            <div class="avatar">DA</div>
            <div class="h-greet-text">
              <div class="small">Good morning</div>
              <div class="name">Diego</div>
            </div>
            <div class="bell">{icon('bell', 13)}<div class="bell-dot"></div></div>
          </div>

          <div class="alert-unread">
            <div class="dot">{icon('msg', 12)}</div>
            <div class="body">
              <div class="head">2 NEW MESSAGES</div>
              <div class="preview">Coach: Don't forget the gi for tomorrow.</div>
            </div>
          </div>

          <div class="rank-card">
            <div class="row">
              <div class="eyebrow">CURRENT RANK</div>
              <div class="badge-active">Active</div>
            </div>
            <h2>Purple<small> belt</small></h2>
            <div class="meta">2 stripes</div>
            <div class="belt"><div class="body" style="background:#7c3aed;"></div><div class="tape"><div class="stripe on"></div><div class="stripe on"></div><div class="stripe"></div><div class="stripe"></div></div></div>
          </div>

          <div class="stats">
            <div class="stat-card accent">
              <div class="head">CHECK-INS</div>
              <div class="big">147</div>
              <div class="lab">all time</div>
            </div>
            <div class="stat-card neutral">
              <div class="head">LAST CLASS</div>
              <div class="big" style="font-size:14pt;">04-26</div>
              <div class="lab">No-Gi Adv.</div>
            </div>
          </div>

          <div class="s-eyebrow">QUICK ACTIONS</div>
          <div class="qa-card">
            <div class="qa-row"><div class="qa-icon-tile accent">{icon('card')}</div><div class="qa-text"><div class="l1">Payments</div><div class="l2">View invoices &amp; pay</div></div><div class="qa-chev">{icon('chev')}</div></div>
            <div class="qa-row"><div class="qa-icon-tile">{icon('cal')}</div><div class="qa-text"><div class="l1">Schedule</div><div class="l2">Classes this week</div></div><div class="qa-chev">{icon('chev')}</div></div>
            <div class="qa-row"><div class="qa-icon-tile">{icon('msg')}</div><div class="qa-text"><div class="l1">Coach chat</div><div class="l2">Message your coach</div></div><div class="qa-badge">2</div><div class="qa-chev">{icon('chev')}</div></div>
          </div>
        </div>
        <div class="tab-bar">
          <div class="tab active">{icon('home', 18)}<div class="tab-label">Home</div></div>
          <div class="tab">{icon('cal', 18)}<div class="tab-label">Schedule</div></div>
          <div class="tab">{icon('pin', 18)}<div class="tab-label">Check in</div></div>
          <div class="tab">{icon('msg', 18)}<div class="tab-label">Chat</div></div>
          <div class="tab">{icon('person', 18)}<div class="tab-label">More</div></div>
        </div>
      </div>
    </div>
    """

def iphone_checkin_in_range():
    return f"""
    <div class="phone">
      <div class="screen">
        <div class="notch"></div>
        <div class="status-bar" style="color:#0f172a;"><span>9:41</span><span>·· ·· 100%</span></div>
        <div class="phone-content">
          <div style="font-family:'Space Grotesk';font-size:14pt;font-weight:800;letter-spacing:-0.5px;margin-bottom:1px;">Check in</div>
          <div style="font-size:7.5pt;color:#94a3b8;margin-bottom:10px;">Seeds 13 BJJ</div>

          <div class="checkin-hero">
            <div class="pin-icon">{icon('pin', 22)}</div>
            <div class="eyebrow">YOU'RE HERE</div>
            <h2>Tap to check in</h2>
            <div class="meters">12 m from the gym</div>
            <div class="pill">{icon('check')} Check me in</div>
          </div>

          <div class="s-eyebrow">OTHER WAYS TO CHECK IN</div>
          <div class="qa-card">
            <div class="qa-row"><div class="qa-icon-tile accent">{icon('face')}</div><div class="qa-text"><div class="l1">Confirm with Face ID</div><div class="l2">Faster — no need to be at the gym</div></div><div class="qa-chev">{icon('chev')}</div></div>
            <div class="qa-row"><div class="qa-icon-tile">{icon('check')}</div><div class="qa-text"><div class="l1">Manual check-in</div><div class="l2">Without GPS or biometric</div></div><div class="qa-chev">{icon('chev')}</div></div>
          </div>
        </div>
        <div class="tab-bar">
          <div class="tab">{icon('home', 18)}<div class="tab-label">Home</div></div>
          <div class="tab">{icon('cal', 18)}<div class="tab-label">Schedule</div></div>
          <div class="tab active">{icon('pin', 18)}<div class="tab-label">Check in</div></div>
          <div class="tab">{icon('msg', 18)}<div class="tab-label">Chat</div></div>
          <div class="tab">{icon('person', 18)}<div class="tab-label">More</div></div>
        </div>
      </div>
    </div>
    """

def iphone_checkin_faceid():
    return f"""
    <div class="phone">
      <div class="screen">
        <div class="notch"></div>
        <div class="status-bar" style="color:#0f172a;"><span>9:41</span><span>·· ·· 100%</span></div>
        <div class="phone-content">
          <div style="font-family:'Space Grotesk';font-size:14pt;font-weight:800;letter-spacing:-0.5px;margin-bottom:1px;">Check in</div>
          <div style="font-size:7.5pt;color:#94a3b8;margin-bottom:10px;">Seeds 13 BJJ</div>
          <div class="checkin-hero" style="filter:blur(1px);opacity:0.6;">
            <div class="pin-icon">{icon('pin', 22)}</div>
            <div class="eyebrow">YOU'RE HERE</div>
            <h2>Tap to check in</h2>
          </div>
        </div>
        <div class="faceid-sheet">
          <div class="face-tag">CONFIRM CHECK-IN</div>
          <div class="face-icon">{icon('face', 30)}</div>
          <div class="face-h">Look at your phone</div>
          <div class="face-cap">Cancel</div>
        </div>
      </div>
    </div>
    """

def iphone_chat():
    return f"""
    <div class="phone">
      <div class="screen">
        <div class="notch"></div>
        <div class="status-bar" style="color:#0f172a;"><span>9:41</span><span>·· ·· 100%</span></div>
        <div class="phone-content" style="padding:38px 0 0; background:#f8fafc;">
          <div style="padding:0 14px 8px;border-bottom:0.5px solid rgba(0,0,0,0.06);">
            <div style="font-family:'Space Grotesk';font-size:13pt;font-weight:800;letter-spacing:-0.4px;">Coach Marco</div>
            <div style="font-size:7pt;color:#94a3b8;">Online · usually replies in 10m</div>
          </div>
          <div style="padding:10px 12px;display:flex;flex-direction:column;">
            <div class="bubble coach">Hey Diego — ready for tomorrow's seminar? 8 AM sharp.</div>
            <div class="bubble mine">Yes coach! I'll bring the new gi.</div>
            <div class="bubble coach">Perfect. Bring your white belt buddy too if he's around.</div>
            <div class="bubble mine">Will do.</div>
            <div class="bubble coach">Don't forget the gi for tomorrow.</div>
          </div>
        </div>
        <div style="position:absolute;bottom:60px;left:0;right:0;padding:8px 10px;background:#fff;border-top:0.5px solid rgba(0,0,0,0.06);display:flex;gap:6px;">
          <div style="flex:1;background:#f1f5f9;border-radius:14px;padding:7px 10px;font-size:8pt;color:#94a3b8;">Type a message…</div>
          <div style="background:#00DC82;width:30px;height:30px;border-radius:15px;display:flex;align-items:center;justify-content:center;color:#0f172a;">{icon('send', 14)}</div>
        </div>
        <div class="tab-bar">
          <div class="tab">{icon('home', 18)}<div class="tab-label">Home</div></div>
          <div class="tab">{icon('cal', 18)}<div class="tab-label">Schedule</div></div>
          <div class="tab">{icon('pin', 18)}<div class="tab-label">Check in</div></div>
          <div class="tab active">{icon('msg', 18)}<div class="tab-label">Chat</div></div>
          <div class="tab">{icon('person', 18)}<div class="tab-label">More</div></div>
        </div>
      </div>
    </div>
    """

def iphone_payment():
    return f"""
    <div class="phone">
      <div class="screen">
        <div class="notch"></div>
        <div class="status-bar" style="color:#0f172a;"><span>9:41</span><span>·· ·· 100%</span></div>
        <div class="phone-content">
          <div style="font-family:'Space Grotesk';font-size:14pt;font-weight:800;letter-spacing:-0.5px;">Pay</div>
          <div style="font-size:7.5pt;color:#94a3b8;margin-bottom:6px;">April membership · Seeds 13 BJJ</div>

          <div class="pay-amount">
            <div class="lab">AMOUNT DUE</div>
            <div class="big">$249.50</div>
            <div class="fee">+ $0.30 processing fee</div>
          </div>

          <div class="stripe-mock">
            <div class="pm-tabs">
              <div class="pm-tab active">Card</div>
              <div class="pm-tab">Bank</div>
              <div class="pm-tab">Apple Pay</div>
            </div>
            <div class="input-line"><span>Card number</span><span class="ph">4242 4242 4242 4242</span></div>
            <div class="input-line"><span>Expiry</span><span class="ph">12/27</span></div>
            <div class="input-line"><span>CVV</span><span class="ph">···</span></div>
          </div>
          <div class="applepay-btn">  Pay $249.80</div>
          <div style="text-align:center;font-size:6.5pt;color:#94a3b8;margin-top:8px;">Processed by Stripe · PCI-DSS Level 1</div>
        </div>
        <div class="tab-bar">
          <div class="tab">{icon('home', 18)}<div class="tab-label">Home</div></div>
          <div class="tab">{icon('cal', 18)}<div class="tab-label">Schedule</div></div>
          <div class="tab">{icon('pin', 18)}<div class="tab-label">Check in</div></div>
          <div class="tab">{icon('msg', 18)}<div class="tab-label">Chat</div></div>
          <div class="tab">{icon('person', 18)}<div class="tab-label">More</div></div>
        </div>
      </div>
    </div>
    """

def iphone_lockscreen():
    return f"""
    <div class="phone">
      <div class="screen">
        <div class="notch"></div>
        <div class="lock-screen">
          <div style="font-size:8.5pt;text-align:center;color:rgba(255,255,255,0.7);margin-bottom:6px;">{icon('lock', 12)}</div>
          <div class="lock-time">9:41</div>
          <div class="lock-date">Tuesday, May 12</div>

          <div class="live-activity" style="margin-bottom:14px;">
            <div class="lv-mark">F4</div>
            <div class="body">
              <div class="lv-eye">SEEDS 13 BJJ</div>
              <div class="lv-l1">No-Gi Advanced</div>
              <div class="lv-l2">Coach Marco · 6 checked in</div>
            </div>
            <div class="lv-time">7:30</div>
          </div>

          <div class="lock-notif">
            <div class="icon-square">F4</div>
            <div class="body">
              <div class="title">You're at Seeds 13 BJJ</div>
              <div class="text">Tap to check in for No-Gi Advanced</div>
              <div class="time-stamp">now</div>
            </div>
          </div>
          <div class="lock-notif">
            <div class="icon-square">F4</div>
            <div class="body">
              <div class="title">Coach Marco</div>
              <div class="text">Don't forget the gi for tomorrow.</div>
              <div class="time-stamp">2m ago</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    """

def member_screens_pages(num_start, total):
    pages = []

    # Page: check-in + Face ID
    pages.append(f"""
    <div class="page">
      {page_header('03 — Member: check-in')}
      <div class="page-content">
        <div class="page-eyebrow">PHASE 5 — NATIVE</div>
        <div class="page-title">Walk up. Get checked in.</div>
        <div class="page-lede">When the phone's GPS or BLE sees the gym within 50 m, the screen flips to the mint hero. One tap and the check-in lands on the front desk's dashboard. For when GPS isn't sure, Face ID is one row away.</div>
        <div class="layout-screens">
          <div>{iphone_checkin_in_range()}<div class="screen-caption"><strong>In-range hero</strong><br>The whole screen becomes the action. Out-of-range it shows the meter count instead of the button.</div></div>
          <div>{iphone_checkin_faceid()}<div class="screen-caption"><strong>Face ID confirm</strong><br>Native iOS sheet — no third-party password, no forgotten PIN. Available only in the native build.</div></div>
        </div>
      </div>
      {footer(num_start, total)}
    </div>
    """)

    # Page: chat + payment
    pages.append(f"""
    <div class="page">
      {page_header('04 — Member: talk &amp; pay')}
      <div class="page-content">
        <div class="page-eyebrow">DAILY USE</div>
        <div class="page-title">Conversations and payments, side by side.</div>
        <div class="page-lede">Coaches and members message each other in a single thread per member. Stripe runs the payments — cards, ACH, Apple Pay, Google Pay — never touching our servers.</div>
        <div class="layout-screens">
          <div>{iphone_chat()}<div class="screen-caption"><strong>Coach chat</strong><br>One thread per member. Push notifications fire on iOS 16.4+ once the PWA is installed (Phase 1) or always in the native build (Phase 5).</div></div>
          <div>{iphone_payment()}<div class="screen-caption"><strong>Payment</strong><br>Stripe Payment Element handles cards, ACH and Apple Pay. The native build adds the iOS sheet over the web embed for a tighter feel.</div></div>
        </div>
      </div>
      {footer(num_start + 1, total)}
    </div>
    """)

    # Page: lock screen + live activity
    pages.append(f"""
    <div class="page">
      {page_header('05 — Phase 5 native: lock screen')}
      <div class="page-content">
        <div class="page-eyebrow">NATIVE-ONLY</div>
        <div class="page-title">Showing up where the member already is.</div>
        <div class="page-lede">Two things only the native app does. A geofence push that lands on the lock screen the moment the member is within 50 m of the gym, and a Live Activity that pins the next class to the dynamic island and lock screen for the hour before it starts.</div>
        <div class="layout-screens">
          <div>{iphone_lockscreen()}<div class="screen-caption"><strong>Geofence push + Live Activity</strong><br>The PWA cannot run in background — these two surfaces require the native build. Right at the top of the lock screen, the timer ticks down to "No-Gi Advanced" with the coach's name; below it, the proximity push asks for one tap to check in.</div></div>
          <div style="max-width:280px;align-self:center;">
            <h3 style="font-family:'Space Grotesk';font-size:13pt;color:#0f172a;font-weight:700;letter-spacing:-0.3px;margin-bottom:8px;">Why these matter</h3>
            <p style="font-size:9pt;line-height:1.55;color:#334155;">Members arriving at the gym don't open the app — their phone is in their pocket. The proximity push is the cue to check in. The Live Activity is the cue to leave home on time.</p>
            <p style="font-size:9pt;line-height:1.55;color:#334155;margin-top:8px;">Both translate to retention numbers: students who check in consistently train more weeks per year, and gym owners who can see check-in rate per student catch dropoffs early.</p>
            <h3 style="font-family:'Space Grotesk';font-size:13pt;color:#0f172a;font-weight:700;letter-spacing:-0.3px;margin:14px 0 6px;">Built on</h3>
            <p style="font-size:9pt;color:#334155;line-height:1.5;">expo-location significant-changes API, Apple Push Notification Service, ActivityKit, and the ARN topic our backend already knows how to address.</p>
          </div>
        </div>
      </div>
      {footer(num_start + 2, total)}
    </div>
    """)

    return pages

def staff_overview(num, total):
    return f"""
    <div class="page">
      {page_header('06 — The owner side')}
      <div class="page-content">
        <div class="page-eyebrow">FOR GYM OWNERS</div>
        <div class="page-title">One screen to run the whole academy.</div>
        <div class="page-lede">The SaaS side is desktop-first because that's where front-desk and ownership work happens. Login lands directly on the dashboard — KPIs, today's classes, a banner for unread messages from members, and one-click triage for everything that needs attention.</div>
        {desktop_dashboard()}
        <div class="screen-caption" style="max-width:6.5in;margin:8px auto 0;"><strong>Dashboard</strong> — the orange banner at the top is new in this version: it surfaces unread member messages straight on the home page so a coach who logs in sees them before clicking around.</div>
      </div>
      {footer(num, total)}
    </div>
    """

def desktop_dashboard():
    return f"""
    <div class="desktop">
      <div style="width:100%;">
        <div class="desktop-bar">
          <div class="dots"><div class="dot red"></div><div class="dot yel"></div><div class="dot grn"></div></div>
          <div class="url">app.fit4academy.com</div>
        </div>
        <div class="staff-app">
          <div class="sidebar">
            <div class="brand"><div class="sb-mark">F4</div><div class="sb-name">Fit4Academy</div></div>
            <div class="sb-section-label">RUN</div>
            <div class="sb-link active">{icon('home',11)} Dashboard</div>
            <div class="sb-link">{icon('users',11)} Members</div>
            <div class="sb-link">{icon('cal',11)} Schedule</div>
            <div class="sb-link">{icon('check',11)} Check-ins</div>
            <div class="sb-section-label">BUSINESS</div>
            <div class="sb-link">{icon('graph',11)} Finance</div>
            <div class="sb-link">{icon('card',11)} Payments</div>
            <div class="sb-section-label">MORE</div>
            <div class="sb-link">{icon('shop',11)} Store</div>
            <div class="sb-link">{icon('trophy',11)} Events</div>
            <div class="sb-link">{icon('bell',11)} Notifications<span class="sb-pill">3</span></div>
            <div class="sb-link">{icon('gear',11)} Settings</div>
          </div>
          <div class="staff-main">
            <div class="staff-h1">Good afternoon, Coach.</div>
            <div class="kpi-row">
              <div class="kpi"><div class="lab">ACTIVE MEMBERS</div><div class="num">248</div><div class="delta">+12 this month</div></div>
              <div class="kpi"><div class="lab">TODAY'S CHECK-INS</div><div class="num">19</div><div class="delta">+5 vs avg</div></div>
              <div class="kpi"><div class="lab">MONTHLY REVENUE</div><div class="num">$12,480</div><div class="delta">+8% vs last</div></div>
              <div class="kpi"><div class="lab">EXPIRING SOON</div><div class="num" style="color:#f59e0b;">7</div><div class="delta" style="color:#94a3b8;">to renew</div></div>
            </div>
            <div class="banner-orange">
              <div class="icn">{icon('msg', 13)}</div>
              <div class="body">
                <div class="h">3 unread messages from members</div>
                <div class="h-sub">Click a name to open the chat thread.</div>
              </div>
            </div>
            <div class="banner-thread"><div class="av-circle">DA</div><div class="body"><div class="name">Diego Almeida</div><div class="preview">Coach, can I train tomorrow at 6 PM?</div></div></div>
            <div class="banner-thread"><div class="av-circle">MT</div><div class="body"><div class="name">Mobile Tester</div><div class="preview">Do we still have class on Saturday?</div></div></div>
            <div class="banner-thread"><div class="av-circle">DV</div><div class="body"><div class="name">Demo Visitor</div><div class="preview">Hi! Just signed up — what's the dress code?</div></div></div>
          </div>
        </div>
      </div>
    </div>
    """

def desktop_members():
    return f"""
    <div class="desktop">
      <div style="width:100%;">
        <div class="desktop-bar">
          <div class="dots"><div class="dot red"></div><div class="dot yel"></div><div class="dot grn"></div></div>
          <div class="url">app.fit4academy.com / members</div>
        </div>
        <div class="staff-app">
          <div class="sidebar">
            <div class="brand"><div class="sb-mark">F4</div><div class="sb-name">Fit4Academy</div></div>
            <div class="sb-section-label">RUN</div>
            <div class="sb-link">{icon('home',11)} Dashboard</div>
            <div class="sb-link active">{icon('users',11)} Members</div>
            <div class="sb-link">{icon('cal',11)} Schedule</div>
            <div class="sb-link">{icon('check',11)} Check-ins</div>
            <div class="sb-section-label">BUSINESS</div>
            <div class="sb-link">{icon('graph',11)} Finance</div>
            <div class="sb-link">{icon('card',11)} Payments</div>
          </div>
          <div class="staff-main">
            <div class="staff-h1">Members <span style="color:#94a3b8;font-size:11pt;font-weight:600;">· 248</span></div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
              <div style="display:flex;gap:6px;">
                <div style="background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:6px 10px;font-size:8pt;color:#475569;">All</div>
                <div style="background:rgba(0,220,130,0.08);border:1px solid rgba(0,220,130,0.30);border-radius:6px;padding:6px 10px;font-size:8pt;color:#00B368;font-weight:600;">Active 224</div>
                <div style="background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:6px 10px;font-size:8pt;color:#475569;">Past due 8</div>
              </div>
              <div style="background:#0f172a;color:#fff;padding:6px 12px;border-radius:6px;font-size:8pt;font-weight:700;display:flex;align-items:center;gap:5px;">{icon('plus', 11)} Add member</div>
            </div>
            <table style="width:100%;font-size:8.5pt;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;border:1px solid #e2e8f0;">
              <thead><tr style="background:#f8fafc;">
                <th style="text-align:left;padding:8px 12px;font-size:7pt;color:#475569;letter-spacing:0.5px;">MEMBER</th>
                <th style="text-align:left;padding:8px 12px;font-size:7pt;color:#475569;letter-spacing:0.5px;">BELT</th>
                <th style="text-align:left;padding:8px 12px;font-size:7pt;color:#475569;letter-spacing:0.5px;">STATUS</th>
                <th style="text-align:left;padding:8px 12px;font-size:7pt;color:#475569;letter-spacing:0.5px;">JOIN DATE</th>
                <th style="text-align:right;padding:8px 12px;font-size:7pt;color:#475569;letter-spacing:0.5px;">CHECK-INS</th>
              </tr></thead>
              <tbody>
                {members_row('Diego Almeida', 'Purple · 2 stripes', 'Active', '2024-08-12', '147')}
                {members_row('Camila Rocha', 'Blue · 4 stripes', 'Active', '2025-01-04', '92')}
                {members_row('Lucas Pereira', 'Brown · 1 stripe', 'Past due', '2023-05-22', '218', warn=True)}
                {members_row('Yuki Tanaka', 'White · 3 stripes', 'Active', '2025-09-10', '38')}
                {members_row('Ana Souza', 'Purple · 0 stripes', 'Active', '2024-11-30', '110')}
                {members_row('Karim Hassan', 'Blue · 2 stripes', 'Active', '2025-03-18', '63')}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
    """

def members_row(name, belt, status, joined, checkins, warn=False):
    if warn:
        status_html = '<span style="background:rgba(245,158,11,0.12);color:#f59e0b;padding:2px 8px;border-radius:999px;font-size:7pt;font-weight:700;">Past due</span>'
    else:
        status_html = '<span style="background:rgba(0,220,130,0.10);color:#00B368;padding:2px 8px;border-radius:999px;font-size:7pt;font-weight:700;">Active</span>'
    return f"""<tr style="border-top:1px solid #f1f5f9;">
      <td style="padding:8px 12px;font-weight:600;">{name}</td>
      <td style="padding:8px 12px;color:#475569;">{belt}</td>
      <td style="padding:8px 12px;">{status_html}</td>
      <td style="padding:8px 12px;color:#475569;">{joined}</td>
      <td style="padding:8px 12px;text-align:right;font-family:'Space Grotesk';font-weight:700;">{checkins}</td>
    </tr>"""

def staff_screens_pages(num_start, total):
    pages = []

    pages.append(f"""
    <div class="page">
      {page_header('07 — Owner: members')}
      <div class="page-content">
        <div class="page-eyebrow">MEMBER ROSTER</div>
        <div class="page-title">Every member, one filterable list.</div>
        <div class="page-lede">A coach answering "who's past due this month" or "how many purple belts do we have" finds the answer in two clicks. Filters at the top, table below, and the action buttons stay in the same place across every list.</div>
        {desktop_members()}
        <div class="screen-caption" style="max-width:6.5in;margin:8px auto 0;"><strong>Members list</strong> — past-due rows are tagged amber so the coach can settle outstanding balances before class. Belt + stripe live next to the name to nudge promotion conversations.</div>
      </div>
      {footer(num_start, total)}
    </div>
    """)

    pages.append(f"""
    <div class="page">
      {page_header('08 — Owner: chat thread')}
      <div class="page-content">
        <div class="page-eyebrow">REPLYING TO A STUDENT</div>
        <div class="page-title">Same chat. Same data. Two views.</div>
        <div class="page-lede">When the coach clicks a member from the orange banner on the dashboard, they land here. The conversation is the same one the member sees in the iPhone app — sent through the same JWT-protected endpoints — just rendered desktop-first.</div>
        {desktop_chat_thread()}
        <div class="screen-caption" style="max-width:6.5in;margin:8px auto 0;"><strong>Single chat thread</strong> — typing indicator, member context (belt, last check-in, pending balance) on the right rail, full history scrolled to the latest unread.</div>
      </div>
      {footer(num_start + 1, total)}
    </div>
    """)

    return pages

def desktop_chat_thread():
    return f"""
    <div class="desktop">
      <div style="width:100%;">
        <div class="desktop-bar">
          <div class="dots"><div class="dot red"></div><div class="dot yel"></div><div class="dot grn"></div></div>
          <div class="url">app.fit4academy.com / staff-chat / 142</div>
        </div>
        <div class="staff-app">
          <div class="sidebar">
            <div class="brand"><div class="sb-mark">F4</div><div class="sb-name">Fit4Academy</div></div>
            <div class="sb-link">{icon('home',11)} Dashboard</div>
            <div class="sb-link">{icon('users',11)} Members</div>
            <div class="sb-link active">{icon('msg',11)} Chat<span class="sb-pill">3</span></div>
            <div class="sb-link">{icon('cal',11)} Schedule</div>
            <div class="sb-link">{icon('card',11)} Payments</div>
          </div>
          <div class="staff-main" style="padding:0;display:flex;">
            <div style="width:160px;background:#fff;border-right:1px solid #e2e8f0;padding:10px 8px;">
              <div style="font-size:7pt;font-weight:700;color:#94a3b8;letter-spacing:0.5px;padding:0 6px 8px;">CONVERSATIONS</div>
              {chat_thread_row('Diego Almeida', 'Coach, can I train tomorr…', '2m', True)}
              {chat_thread_row('Mobile Tester', 'Do we still have class on …', '14m', True)}
              {chat_thread_row('Demo Visitor', 'Hi! Just signed up — what…', '1h', True)}
              {chat_thread_row('Camila Rocha', 'Thank you coach!', '2d', False)}
              {chat_thread_row('Yuki Tanaka', 'Got it.', '5d', False)}
            </div>
            <div style="flex:1;background:#f8fafc;display:flex;flex-direction:column;">
              <div style="padding:11px 14px;border-bottom:1px solid #e2e8f0;background:#fff;display:flex;align-items:center;gap:10px;">
                <div style="width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#00DC82,#00B368);font-weight:800;font-size:10pt;color:#0f172a;display:flex;align-items:center;justify-content:center;font-family:'Space Grotesk';">DA</div>
                <div style="flex:1;">
                  <div style="font-weight:700;font-size:9.5pt;">Diego Almeida</div>
                  <div style="font-size:7pt;color:#94a3b8;">Purple · 2 stripes · 147 check-ins · last 04-26</div>
                </div>
                <div style="font-size:7pt;color:#00B368;font-weight:700;background:rgba(0,220,130,0.10);padding:2px 8px;border-radius:999px;">Active</div>
              </div>
              <div style="flex:1;padding:14px;display:flex;flex-direction:column;gap:6px;">
                <div class="bubble coach" style="font-size:8.5pt;">Hey Coach! Posso treinar amanhã às 6 PM?</div>
                <div class="bubble mine" style="font-size:8.5pt;background:#fff;color:#0f172a;border:1px solid #e2e8f0;align-self:flex-start;border-radius:14px 14px 14px 4px;margin-left:0;">Pode sim! Aula avançada às 18h, técnica nova de raspagem.</div>
                <div class="bubble coach" style="font-size:8.5pt;">Show, vou levar o gi novo.</div>
              </div>
              <div style="padding:10px;background:#fff;border-top:1px solid #e2e8f0;display:flex;gap:6px;">
                <div style="flex:1;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:7px 11px;font-size:8pt;color:#94a3b8;">Reply to Diego…</div>
                <div style="background:linear-gradient(135deg,#00DC82,#00B368);color:#0f172a;font-weight:700;font-size:8pt;padding:7px 14px;border-radius:8px;">Send</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    """

def chat_thread_row(name, preview, time, unread):
    border = 'border-left:3px solid #f59e0b;' if unread else 'border-left:3px solid transparent;'
    bg = 'background:rgba(245,158,11,0.06);' if unread else ''
    return f"""<div style="padding:7px 8px;{border}{bg}border-radius:5px;margin-bottom:2px;">
      <div style="display:flex;justify-content:space-between;font-size:7.5pt;font-weight:{700 if unread else 600};">{name}<span style="color:#94a3b8;font-size:6.5pt;">{time}</span></div>
      <div style="font-size:6.5pt;color:#475569;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{preview}</div>
    </div>"""

def roadmap_page(num, total):
    return f"""
    <div class="page">
      {page_header('09 — Roadmap')}
      <div class="page-content">
        <div class="page-eyebrow">WHERE WE ARE</div>
        <div class="page-title">Five phases. PWA in production today.</div>
        <div class="page-lede">Phase 0–1 are live in production at <code>web-production-83f27.up.railway.app/app/</code>. Phase 2 is mid-flight — chat, payments, and dashboards are working; push and the in-app store are next. Phases 4–5 unlock the native-only features shown in this deck.</div>
        <div class="roadmap">
          <div class="phase done">
            <div class="stat-pill">DONE</div>
            <div class="num">0</div>
            <div class="nm">Foundation</div>
            <div class="ds">JWT auth, member &amp; staff API, mobile scaffold, login + signup screens.</div>
          </div>
          <div class="phase done">
            <div class="stat-pill">DONE</div>
            <div class="num">1</div>
            <div class="nm">PWA beta</div>
            <div class="ds">Expo web export served at /app/. iPhone "Add to Home Screen" works; install prompt embedded.</div>
          </div>
          <div class="phase now">
            <div class="stat-pill">IN PROGRESS</div>
            <div class="num">2</div>
            <div class="nm">Member features</div>
            <div class="ds">Dashboard, payments (PCI-fixed), chat with unread badges, schedule. Push notifications next.</div>
          </div>
          <div class="phase future">
            <div class="stat-pill">NEXT</div>
            <div class="num">3</div>
            <div class="nm">Owner features</div>
            <div class="ds">KPIs, members table, today's classes, manual payment flow, quick check-in for the front desk.</div>
          </div>
          <div class="phase future">
            <div class="stat-pill">PHASE 5</div>
            <div class="num">4·5</div>
            <div class="nm">Native publish</div>
            <div class="ds">App Store + Play Store. Unlocks geofence-arrival push, biometric confirm, BLE beacon check-in, Live Activities, Apple Pay native sheet.</div>
          </div>
        </div>

        <h3 style="font-family:'Space Grotesk';font-size:13pt;color:#0f172a;font-weight:700;letter-spacing:-0.3px;margin:22px 0 8px;">Trigger to ship the native build</h3>
        <p style="font-size:9.5pt;color:#334155;line-height:1.55;">Phase 5 is gated on market signal, not time. We move when one of these fires:</p>
        <ul style="font-size:9.5pt;color:#334155;line-height:1.6;margin-top:6px;padding-left:22px;">
          <li>5+ academies paying a recurring subscription (validation of demand)</li>
          <li>A top-3 gym owner says "I'd buy if you had geofence-arrival push" (validation of feature as the wedge)</li>
          <li>Apple or Google changes a rule that breaks something we rely on in the PWA</li>
        </ul>
      </div>
      {footer(num, total)}
    </div>
    """

def cta_page(num, total):
    return """
    <div class="page cta-page">
      <div class="cta-pill" style="align-self:flex-start;border-color:rgba(110,231,183,0.4);color:#6ee7b7;font-size:9pt;letter-spacing:1px;">PHASE 5 PRODUCT VISION</div>
      <h1 style="margin-top:30px;">Run your academy.<br><em>Not your spreadsheets.</em></h1>
      <div class="cta-sub">Owners stop juggling WhatsApp groups, paper sign-in sheets, and spreadsheets. Members stop wondering if their belt is logged or if their payment cleared. Both sides know — exactly, in real time — what's going on.</div>

      <div class="cta-row">
        <div class="cta-pill">Live: app.fit4academy.com/app/</div>
        <div class="cta-pill">Native iOS &amp; Android · Phase 5</div>
        <div class="cta-pill solid">Built on Stripe, Expo, Flask, PostgreSQL.</div>
      </div>

      <div style="margin-top:auto;padding-top:40px;border-top:1px solid rgba(255,255,255,0.10);font-size:9pt;color:rgba(255,255,255,0.45);display:flex;justify-content:space-between;">
        <div>Fit4Academy · 2026 · Confidential</div>
        <div>v1.0 · Product vision</div>
      </div>
    </div>
    """


# ────────────────────────────────────────────────────────────────────
#  Build
# ────────────────────────────────────────────────────────────────────

def build_html():
    pages = []
    # Cover
    pages.append(cover())
    # Total computed lazily — placeholders replaced after assembly
    placeholder_total = "{TOTAL}"
    # Brand
    pages.append(brand_page("{N1}", placeholder_total))
    # Member overview
    pages.append(member_overview("{N2}", placeholder_total))
    # Member screens
    member_pages = member_screens_pages(3, placeholder_total)
    member_pages = [p.replace(str(3), "{N3}", 1).replace(str(4), "{N4}", 1).replace(str(5), "{N5}", 1) for p in member_pages]
    # We'll just reassign cleanly below — simpler.

    # Reset and rebuild with sequential numbering
    final_pages = [cover()]
    body_pages = []
    body_pages.append(brand_page(0, 0))
    body_pages.append(member_overview(0, 0))
    body_pages.extend(member_screens_pages(0, 0))
    body_pages.append(staff_overview(0, 0))
    body_pages.extend(staff_screens_pages(0, 0))
    body_pages.append(roadmap_page(0, 0))
    body_pages.append(cta_page(0, 0))

    total = 1 + len(body_pages)  # cover + body pages

    # Replace footer page numbers per page
    rebuilt = [final_pages[0]]
    for i, p in enumerate(body_pages, start=2):  # body starts at page 2 (cover is 1)
        # Crude but effective: replace the footer placeholder values
        # The footer was generated with 0/0 — substitute with i/total
        replaced = p.replace(
            '<div>0 / 0</div>',
            f'<div>{i} / {total}</div>',
        )
        rebuilt.append(replaced)

    full = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Fit4Academy — Phase 5 Product Vision</title>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=Space+Grotesk:wght@500;600;700;800&display=swap" rel="stylesheet">
  <style>{CSS}</style>
</head>
<body>
{''.join(rebuilt)}
</body>
</html>"""
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(full)
    print(f"Wrote HTML: {HTML_PATH}")


def build_pdf():
    chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    if not os.path.exists(chrome):
        print("Chrome not found at expected path.", file=sys.stderr)
        sys.exit(1)
    cmd = [
        chrome,
        '--headless=new',
        '--disable-gpu',
        '--no-sandbox',
        '--no-pdf-header-footer',
        '--run-all-compositor-stages-before-draw',
        '--virtual-time-budget=10000',
        f'--print-to-pdf={PDF_PATH}',
        f'file://{HTML_PATH}',
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not os.path.exists(PDF_PATH):
        print("PDF generation failed.", file=sys.stderr)
        print("STDOUT:", result.stdout, file=sys.stderr)
        print("STDERR:", result.stderr, file=sys.stderr)
        sys.exit(1)
    size = os.path.getsize(PDF_PATH) / 1024
    print(f"Wrote PDF: {PDF_PATH} ({size:.1f} KB)")


if __name__ == '__main__':
    build_html()
    build_pdf()
