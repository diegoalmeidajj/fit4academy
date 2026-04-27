import { useCallback, useEffect, useState } from 'react';
import {
  View,
  Text,
  Pressable,
  ScrollView,
  Switch,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useTheme, radius, spacing } from '@/lib/theme';
import { useAuth } from '@/store/auth';
import { useThemeMode } from '@/store/themeMode';
import { apiGet, apiPost } from '@/lib/api';
import { authenticate, biometricCapability } from '@/lib/biometric';
import { Card } from '@/components/Card';
import { Button } from '@/components/Button';

const THEME_OPTIONS: { value: 'system' | 'light' | 'dark'; label: string; emoji: string }[] = [
  { value: 'system', label: 'System', emoji: '🌗' },
  { value: 'light', label: 'Light', emoji: '☀️' },
  { value: 'dark', label: 'Dark', emoji: '🌙' },
];

export default function ProfileScreen() {
  const t = useTheme();
  const me = useAuth(s => s.me);
  const logout = useAuth(s => s.logout);
  const themeMode = useThemeMode(s => s.mode);
  const setThemeMode = useThemeMode(s => s.setMode);
  const [bioCap, setBioCap] = useState({ available: false, label: '' });
  const [bioEnabled, setBioEnabled] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const cap = await biometricCapability();
    setBioCap({ available: cap.available, label: cap.label || 'Biometric' });
    const r = await apiGet<{ enabled: boolean }>('/api/v1/me/biometric');
    if (r.ok) setBioEnabled(r.data.enabled);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function toggleBiometric(next: boolean) {
    if (busy) return;
    setBusy(true);
    if (next) {
      const auth = await authenticate(`Enable ${bioCap.label}`);
      if (!auth.ok) { setBusy(false); return; }
    }
    const r = await apiPost<{ enabled: boolean }>('/api/v1/me/biometric', { enabled: next });
    if (r.ok) setBioEnabled(r.data.enabled);
    setBusy(false);
  }

  if (!me || me.type !== 'member') return null;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.tokens.bg.canvas }}>
      <ScrollView
        contentContainerStyle={{ padding: spacing.xl, paddingBottom: spacing.xxxl }}
        showsVerticalScrollIndicator={false}
      >
        <Text style={{ fontSize: 28, fontWeight: '800', color: t.tokens.text.primary, marginBottom: spacing.lg, letterSpacing: -0.5 }}>
          Profile
        </Text>

        <Card style={{ marginBottom: spacing.md }}>
          <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginBottom: 4 }}>NAME</Text>
          <Text style={{ ...t.type.h3, color: t.tokens.text.primary }}>{me.first_name} {me.last_name}</Text>
        </Card>
        <Card style={{ marginBottom: spacing.md }}>
          <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginBottom: 4 }}>EMAIL</Text>
          <Text style={{ ...t.type.h3, color: t.tokens.text.primary }}>{me.email || '—'}</Text>
        </Card>
        <Card style={{ marginBottom: spacing.md }}>
          <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginBottom: 4 }}>PHONE</Text>
          <Text style={{ ...t.type.h3, color: t.tokens.text.primary }}>{me.phone || '—'}</Text>
        </Card>

        {/* THEME */}
        <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginTop: spacing.lg, marginBottom: spacing.sm, textTransform: 'uppercase', letterSpacing: 0.6 }}>
          Appearance
        </Text>
        <Card style={{ marginBottom: spacing.md }}>
          <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginBottom: spacing.sm }}>THEME</Text>
          <View style={{ flexDirection: 'row', gap: 8 }}>
            {THEME_OPTIONS.map((opt) => {
              const active = themeMode === opt.value;
              return (
                <Pressable
                  key={opt.value}
                  onPress={() => setThemeMode(opt.value)}
                  style={{
                    flex: 1,
                    paddingVertical: 12,
                    paddingHorizontal: 8,
                    borderRadius: radius.md,
                    borderWidth: 1.5,
                    borderColor: active ? t.tokens.brand.accent : t.tokens.border.default,
                    backgroundColor: active ? t.tokens.bg.accentSoft : 'transparent',
                    alignItems: 'center',
                  }}
                >
                  <Text style={{ fontSize: 22, marginBottom: 4 }}>{opt.emoji}</Text>
                  <Text style={{
                    fontSize: 12,
                    fontWeight: '700',
                    color: active ? t.tokens.text.accent : t.tokens.text.secondary,
                  }}>
                    {opt.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </Card>

        {/* SECURITY */}
        <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginTop: spacing.lg, marginBottom: spacing.sm, textTransform: 'uppercase', letterSpacing: 0.6 }}>
          Security
        </Text>
        <Card style={{ marginBottom: spacing.md, flexDirection: 'row', alignItems: 'center' }}>
          <View style={{ flex: 1 }}>
            <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginBottom: 4 }}>
              {bioCap.label || 'Biometric login'}
            </Text>
            <Text style={{ ...t.type.body, color: t.tokens.text.secondary, lineHeight: 20 }}>
              {bioCap.available
                ? `Use ${bioCap.label} to sign in to this app faster.`
                : 'Not available on this device.'}
            </Text>
          </View>
          {busy ? (
            <ActivityIndicator color={t.tokens.brand.accent} />
          ) : (
            <Switch
              value={!!bioEnabled}
              onValueChange={toggleBiometric}
              disabled={!bioCap.available}
              trackColor={{ true: t.tokens.brand.accent, false: t.tokens.border.default }}
              thumbColor="#fff"
            />
          )}
        </Card>

        <View style={{ marginTop: spacing.xl }}>
          <Button label="Sign out" variant="danger" onPress={logout} />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
