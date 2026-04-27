/**
 * InstallPrompt — encourages a member opening the PWA in a browser tab to
 * (1) save it to their home screen, and (2) enable push notifications.
 *
 * Only rendered on web. On native we return null because the app is already
 * "installed" through the App Store / Play Store equivalent.
 *
 * Push notifications on iOS Safari only fire AFTER the user has added the
 * site to their home screen and re-opens the standalone PWA — that's why we
 * frame this as two ordered steps, not a single "enable notifications" CTA.
 */
import { useEffect, useState } from 'react';
import { Platform, Pressable, Text, View } from 'react-native';

import { useTheme, radius, spacing } from '@/lib/theme';
import { Icon } from '@/components/Icon';

const DISMISS_KEY = 'f4a:install_dismissed';

type DeviceKind = 'ios' | 'android' | 'desktop';

function detectDevice(): DeviceKind {
  if (typeof navigator === 'undefined') return 'desktop';
  const ua = navigator.userAgent || '';
  if (/iPad|iPhone|iPod/.test(ua)) return 'ios';
  if (/Android/.test(ua)) return 'android';
  return 'desktop';
}

function isStandalone(): boolean {
  if (typeof window === 'undefined') return true;
  // iOS Safari exposes a non-standard navigator.standalone flag.
  const iosStandalone = (window.navigator as { standalone?: boolean }).standalone === true;
  const mediaStandalone = window.matchMedia?.('(display-mode: standalone)').matches === true;
  return iosStandalone || mediaStandalone;
}

export function InstallPrompt() {
  const t = useTheme();
  const [visible, setVisible] = useState(false);
  const [device, setDevice] = useState<DeviceKind>('desktop');
  const [installEvent, setInstallEvent] = useState<{
    prompt: () => Promise<void>;
    userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
  } | null>(null);

  useEffect(() => {
    if (Platform.OS !== 'web') return;
    if (isStandalone()) return;
    try {
      if (window.localStorage?.getItem(DISMISS_KEY) === '1') return;
    } catch {
      // localStorage can throw in private mode — fail open and show prompt.
    }
    setDevice(detectDevice());
    setVisible(true);

    // Chrome/Edge fire `beforeinstallprompt` when the site qualifies for an
    // install. Capture it so the user can install with one tap on Android.
    const handler = (e: Event) => {
      e.preventDefault();
      setInstallEvent(e as unknown as typeof installEvent extends infer T ? T : never);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  if (Platform.OS !== 'web' || !visible) return null;

  function dismiss() {
    setVisible(false);
    try { window.localStorage?.setItem(DISMISS_KEY, '1'); } catch {}
  }

  async function triggerInstall() {
    if (!installEvent) return;
    await installEvent.prompt();
    const choice = await installEvent.userChoice;
    if (choice.outcome === 'accepted') dismiss();
  }

  const headline = device === 'ios'
    ? 'Install Fit4Academy on your iPhone'
    : device === 'android'
    ? 'Install Fit4Academy on your phone'
    : 'Install Fit4Academy';

  const steps =
    device === 'ios'
      ? [
          { n: '1', label: 'Tap the Share button at the bottom of Safari.' },
          { n: '2', label: 'Choose "Add to Home Screen".' },
          { n: '3', label: 'Open from your home screen and allow notifications.' },
        ]
      : device === 'android'
      ? [
          { n: '1', label: installEvent ? 'Tap "Install" below.' : 'Tap the menu (three dots) in Chrome.' },
          { n: '2', label: installEvent ? 'Confirm in the prompt.' : 'Choose "Install app".' },
          { n: '3', label: 'Open the new app icon and allow notifications.' },
        ]
      : [
          { n: '1', label: 'Open this page on your phone for the full experience.' },
          { n: '2', label: 'On iPhone (Safari) or Android (Chrome), add to home screen.' },
        ];

  return (
    <View
      style={{
        marginHorizontal: spacing.xl,
        marginTop: spacing.md,
        borderRadius: radius.lg,
        borderWidth: 1,
        borderColor: t.tokens.border.accent,
        backgroundColor: t.tokens.bg.accentSoft,
        padding: spacing.lg,
      }}
    >
      <View style={{ flexDirection: 'row', alignItems: 'flex-start', gap: spacing.md }}>
        <View
          style={{
            width: 36, height: 36, borderRadius: 10,
            backgroundColor: t.tokens.brand.accent,
            alignItems: 'center', justifyContent: 'center',
            shadowColor: t.tokens.brand.accent,
            shadowOpacity: 0.3,
            shadowRadius: 12,
            shadowOffset: { width: 0, height: 4 },
            elevation: 4,
          }}
        >
          <Text style={{ color: '#0f172a', fontWeight: '800', fontSize: 14, letterSpacing: -0.5 }}>F4</Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={{ fontSize: 15, fontWeight: '700', color: t.tokens.text.primary, letterSpacing: -0.2 }}>
            {headline}
          </Text>
          <Text style={{ fontSize: 12, color: t.tokens.text.secondary, marginTop: 2, lineHeight: 17 }}>
            Get push notifications, faster load times, and a real app icon — no App Store needed.
          </Text>
        </View>
        <Pressable
          onPress={dismiss}
          hitSlop={8}
          style={({ pressed }) => ({
            width: 28, height: 28, borderRadius: 14,
            alignItems: 'center', justifyContent: 'center',
            opacity: pressed ? 0.5 : 0.7,
          })}
        >
          <Icon name="close" size={16} color={t.tokens.text.muted} />
        </Pressable>
      </View>

      <View style={{ marginTop: spacing.md, gap: 8 }}>
        {steps.map(s => (
          <View key={s.n} style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 10 }}>
            <View
              style={{
                width: 20, height: 20, borderRadius: 10,
                backgroundColor: t.tokens.bg.surface,
                borderWidth: 1, borderColor: t.tokens.border.accent,
                alignItems: 'center', justifyContent: 'center',
                marginTop: 1,
              }}
            >
              <Text style={{ fontSize: 11, fontWeight: '700', color: t.tokens.brand.accent }}>{s.n}</Text>
            </View>
            <Text style={{ fontSize: 13, color: t.tokens.text.secondary, flex: 1, lineHeight: 19 }}>
              {s.label}
            </Text>
          </View>
        ))}
      </View>

      {device === 'android' && installEvent && (
        <Pressable
          onPress={triggerInstall}
          style={({ pressed }) => ({
            marginTop: spacing.md,
            backgroundColor: t.tokens.brand.accent,
            paddingVertical: 11,
            borderRadius: radius.sm,
            alignItems: 'center',
            opacity: pressed ? 0.85 : 1,
          })}
        >
          <Text style={{ color: '#0f172a', fontWeight: '800', fontSize: 14, letterSpacing: 0.2 }}>
            Install Fit4Academy
          </Text>
        </Pressable>
      )}
    </View>
  );
}
