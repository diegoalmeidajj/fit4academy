import { useCallback, useEffect, useState } from 'react';
import {
  View, Text, ActivityIndicator, Alert, ScrollView, Pressable,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect } from 'expo-router';

import { useTheme, radius, spacing } from '@/lib/theme';
import { apiGet, apiPost } from '@/lib/api';
import {
  Coords, distanceMeters, getCurrentPosition, requestForegroundPermission,
} from '@/lib/geofence';
import { authenticate, biometricCapability } from '@/lib/biometric';
import { Button } from '@/components/Button';
import { Icon } from '@/components/Icon';

type GeofenceInfo = {
  academy_id: number; name: string; lat: number; lng: number; radius: number; configured: boolean;
};

type Status = 'idle' | 'requesting_perm' | 'locating' | 'ready' | 'submitting' | 'done' | 'error';

const ERR_MAP: Record<string, string> = {
  too_soon: 'You just checked in. Wait a minute and try again.',
  network_error: "Can't reach the server.",
  invalid_method: 'Invalid check-in method.',
};

// Fallback when the academy has not configured a custom radius. 50m is tight
// enough to mean "the member is physically at the door", loose enough to
// account for GPS jitter on a consumer phone.
const RADIUS_DEFAULT_M = 50;

export default function CheckinScreen() {
  const t = useTheme();
  const [geo, setGeo] = useState<GeofenceInfo | null>(null);
  const [pos, setPos] = useState<Coords | null>(null);
  const [permGranted, setPermGranted] = useState<boolean | null>(null);
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);
  const [bio, setBio] = useState({ available: false, label: '' });

  const effectiveRadius = geo?.radius && geo.radius > 0 ? geo.radius : RADIUS_DEFAULT_M;
  const distance = geo && pos ? distanceMeters({ lat: geo.lat, lng: geo.lng }, pos) : null;
  const insideRadius = distance != null ? distance <= effectiveRadius : false;
  const checkedIn = status === 'done';

  const refresh = useCallback(async () => {
    setError(null);
    setStatus('locating');
    const cap = await biometricCapability();
    setBio({ available: cap.available, label: cap.label });
    const g = await apiGet<GeofenceInfo>('/api/v1/me/academy/geofence');
    if (g.ok) setGeo(g.data);
    const perm = await requestForegroundPermission();
    setPermGranted(perm.granted);
    if (perm.granted) {
      const p = await getCurrentPosition();
      setPos(p);
    }
    setStatus('ready');
  }, []);

  useFocusEffect(useCallback(() => { refresh(); }, [refresh]));
  useEffect(() => { refresh(); }, [refresh]);

  async function submit(method: 'manual' | 'geofence' | 'biometric') {
    if (status === 'submitting') return;
    setError(null);
    if (method === 'biometric') {
      if (!bio.available) {
        Alert.alert('Biometric not available', 'Use the manual check-in for now.');
        return;
      }
      const auth = await authenticate('Confirm your check-in');
      if (!auth.ok) {
        if (auth.error !== 'cancelled' && auth.error !== 'user_cancel') {
          setError('Authentication failed. Try again.');
        }
        return;
      }
    }
    setStatus('submitting');
    const r = await apiPost('/api/v1/me/checkins', { method });
    setStatus(r.ok ? 'done' : 'error');
    if (!r.ok) {
      setError(ERR_MAP[r.error || ''] || r.error || 'Something went wrong.');
    } else {
      setTimeout(() => setStatus('ready'), 2400);
    }
  }

  // — Render —

  if (!geo?.configured) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: t.tokens.bg.canvas }}>
        <ScrollView contentContainerStyle={{ padding: spacing.xl }}>
          <Text style={{ fontSize: 28, fontWeight: '800', color: t.tokens.text.primary, letterSpacing: -0.5 }}>
            Check in
          </Text>
          <View
            style={{
              marginTop: spacing.xl,
              padding: spacing.lg,
              borderRadius: radius.lg,
              backgroundColor: t.tokens.bg.warningSoft,
              borderWidth: 1,
              borderColor: t.tokens.border.subtle,
            }}
          >
            <Text style={{ fontSize: 15, fontWeight: '600', color: t.tokens.text.warning }}>
              Gym location not configured
            </Text>
            <Text style={{ fontSize: 13, color: t.tokens.text.secondary, marginTop: 6, lineHeight: 19 }}>
              Your gym hasn't pinned its address yet. Ask the front desk to set it,
              and you'll be able to use geofence + manual check-ins from here.
            </Text>
          </View>
          <View style={{ marginTop: spacing.lg }}>
            <Button
              label="Manual check-in"
              onPress={() => submit('manual')}
              loading={status === 'submitting'}
              variant="secondary"
            />
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.tokens.bg.canvas }}>
      <ScrollView
        contentContainerStyle={{ padding: spacing.xl, paddingBottom: spacing.xxxl }}
        showsVerticalScrollIndicator={false}
      >
        <Text style={{ fontSize: 28, fontWeight: '800', color: t.tokens.text.primary, letterSpacing: -0.5 }}>
          Check in
        </Text>
        <Text style={{ fontSize: 13, color: t.tokens.text.muted, marginTop: 4 }}>
          {geo?.name || 'Your academy'}
        </Text>

        {/* HERO — different visuals depending on state */}
        {checkedIn ? (
          <CheckedInHero />
        ) : insideRadius ? (
          <InRangeHero
            distance={distance!}
            onCheckIn={() => submit('geofence')}
            submitting={status === 'submitting'}
          />
        ) : permGranted === false ? (
          <PermissionDeniedHero />
        ) : distance == null ? (
          <LocatingHero />
        ) : (
          <OutOfRangeHero distance={distance} radius={effectiveRadius} />
        )}

        {/* Secondary actions — always visible so manual + biometric are first-class */}
        <Text
          style={{
            ...t.type.overline,
            color: t.tokens.text.muted,
            marginTop: spacing.xl,
            marginBottom: spacing.md,
          }}
        >
          OTHER WAYS TO CHECK IN
        </Text>

        <View
          style={{
            backgroundColor: t.tokens.bg.surface,
            borderRadius: radius.lg,
            borderWidth: 1,
            borderColor: t.tokens.border.subtle,
            overflow: 'hidden',
          }}
        >
          {bio.available && (
            <Pressable
              onPress={() => submit('biometric')}
              disabled={status === 'submitting'}
              style={({ pressed }) => ({
                flexDirection: 'row',
                alignItems: 'center',
                gap: spacing.md,
                paddingVertical: 14,
                paddingHorizontal: spacing.lg,
                backgroundColor: pressed ? t.tokens.bg.surfaceAlt : 'transparent',
                opacity: status === 'submitting' ? 0.5 : 1,
              })}
            >
              <View
                style={{
                  width: 36, height: 36, borderRadius: 10,
                  backgroundColor: t.tokens.bg.accentSoft,
                  alignItems: 'center', justifyContent: 'center',
                }}
              >
                <Icon name="face-id" size={18} color={t.tokens.brand.accent} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={{ fontSize: 15, fontWeight: '600', color: t.tokens.text.primary }}>
                  Confirm with {bio.label}
                </Text>
                <Text style={{ fontSize: 12, color: t.tokens.text.muted, marginTop: 1 }}>
                  Faster — no need to be at the gym
                </Text>
              </View>
              <Icon name="chevron-right" size={18} color={t.tokens.text.disabled} />
            </Pressable>
          )}
          <Pressable
            onPress={() => submit('manual')}
            disabled={status === 'submitting'}
            style={({ pressed }) => ({
              flexDirection: 'row',
              alignItems: 'center',
              gap: spacing.md,
              paddingVertical: 14,
              paddingHorizontal: spacing.lg,
              borderTopWidth: bio.available ? 0.5 : 0,
              borderTopColor: t.tokens.border.subtle,
              backgroundColor: pressed ? t.tokens.bg.surfaceAlt : 'transparent',
              opacity: status === 'submitting' ? 0.5 : 1,
            })}
          >
            <View
              style={{
                width: 36, height: 36, borderRadius: 10,
                backgroundColor: t.tokens.bg.surfaceAlt,
                alignItems: 'center', justifyContent: 'center',
              }}
            >
              <Icon name="check-circle" size={18} color={t.tokens.text.secondary} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={{ fontSize: 15, fontWeight: '600', color: t.tokens.text.primary }}>
                Manual check-in
              </Text>
              <Text style={{ fontSize: 12, color: t.tokens.text.muted, marginTop: 1 }}>
                Without GPS or biometric
              </Text>
            </View>
            <Icon name="chevron-right" size={18} color={t.tokens.text.disabled} />
          </Pressable>
        </View>

        {error && (
          <Text style={{ color: t.tokens.text.danger, fontSize: 13, textAlign: 'center', marginTop: spacing.md }}>
            {error}
          </Text>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

// ─── Hero variants ────────────────────────────────────────────────

function InRangeHero({
  distance, onCheckIn, submitting,
}: { distance: number; onCheckIn: () => void; submitting: boolean }) {
  const t = useTheme();
  return (
    <View
      style={{
        marginTop: spacing.xl,
        borderRadius: radius.xl,
        backgroundColor: t.tokens.brand.accent,
        padding: spacing.xl,
        paddingVertical: spacing.xxl,
        alignItems: 'center',
        shadowColor: t.tokens.brand.accent,
        shadowOpacity: t.mode === 'dark' ? 0.5 : 0.35,
        shadowRadius: 32,
        shadowOffset: { width: 0, height: 16 },
        elevation: 12,
      }}
    >
      <View
        style={{
          width: 64, height: 64, borderRadius: 32,
          backgroundColor: 'rgba(15,23,42,0.15)',
          alignItems: 'center', justifyContent: 'center',
          marginBottom: spacing.md,
        }}
      >
        <Icon name="pin" size={32} color="#0f172a" />
      </View>
      <Text style={{ fontSize: 13, fontWeight: '700', color: 'rgba(15,23,42,0.7)', letterSpacing: 1.2 }}>
        YOU'RE HERE
      </Text>
      <Text
        style={{
          fontSize: 36,
          fontWeight: '800',
          color: '#0f172a',
          letterSpacing: -1.2,
          marginTop: 8,
          textAlign: 'center',
        }}
      >
        Tap to check in
      </Text>
      <Text style={{ fontSize: 13, color: 'rgba(15,23,42,0.7)', marginTop: 6 }}>
        {Math.round(distance)} m from the gym
      </Text>

      <Pressable
        onPress={onCheckIn}
        disabled={submitting}
        style={({ pressed }) => ({
          marginTop: spacing.xl,
          backgroundColor: '#0f172a',
          paddingVertical: 18,
          paddingHorizontal: 48,
          borderRadius: radius.pill,
          flexDirection: 'row',
          alignItems: 'center',
          gap: 10,
          alignSelf: 'stretch',
          justifyContent: 'center',
          opacity: submitting ? 0.6 : pressed ? 0.85 : 1,
          transform: [{ scale: pressed ? 0.98 : 1 }],
          shadowColor: '#0f172a',
          shadowOpacity: 0.3,
          shadowRadius: 12,
          shadowOffset: { width: 0, height: 6 },
          elevation: 6,
        })}
      >
        {submitting ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <>
            <Icon name="check" size={20} color="#fff" />
            <Text style={{ fontSize: 17, fontWeight: '800', color: '#fff', letterSpacing: 0.2 }}>
              Check me in
            </Text>
          </>
        )}
      </Pressable>
    </View>
  );
}

function CheckedInHero() {
  const t = useTheme();
  return (
    <View
      style={{
        marginTop: spacing.xl,
        borderRadius: radius.xl,
        backgroundColor: t.tokens.bg.accentSoft,
        borderWidth: 1,
        borderColor: t.tokens.border.accent,
        padding: spacing.xl,
        paddingVertical: spacing.xxl,
        alignItems: 'center',
      }}
    >
      <View
        style={{
          width: 72, height: 72, borderRadius: 36,
          backgroundColor: t.tokens.brand.accent,
          alignItems: 'center', justifyContent: 'center',
        }}
      >
        <Icon name="check" size={40} color="#0f172a" />
      </View>
      <Text
        style={{
          fontSize: 28,
          fontWeight: '800',
          color: t.tokens.text.primary,
          letterSpacing: -0.8,
          marginTop: spacing.md,
        }}
      >
        Checked in!
      </Text>
      <Text style={{ fontSize: 14, color: t.tokens.text.muted, marginTop: 4 }}>
        Have a great training session.
      </Text>
    </View>
  );
}

function OutOfRangeHero({ distance, radius: r }: { distance: number; radius: number }) {
  const t = useTheme();
  return (
    <View
      style={{
        marginTop: spacing.xl,
        borderRadius: radius.xl,
        backgroundColor: t.tokens.bg.surface,
        borderWidth: 1,
        borderColor: t.tokens.border.subtle,
        padding: spacing.xl,
        paddingVertical: spacing.xxl,
        alignItems: 'center',
      }}
    >
      <View
        style={{
          width: 64, height: 64, borderRadius: 32,
          backgroundColor: t.tokens.bg.surfaceAlt,
          alignItems: 'center', justifyContent: 'center',
          marginBottom: spacing.md,
        }}
      >
        <Icon name="pin" size={28} color={t.tokens.text.muted} />
      </View>
      <Text style={{ fontSize: 12, fontWeight: '700', color: t.tokens.text.muted, letterSpacing: 1 }}>
        DISTANCE TO GYM
      </Text>
      <Text
        style={{
          fontSize: 48,
          fontWeight: '800',
          color: t.tokens.text.primary,
          letterSpacing: -2,
          marginTop: 6,
        }}
      >
        {Math.round(distance)} m
      </Text>
      <Text style={{ fontSize: 13, color: t.tokens.text.muted, marginTop: 6, textAlign: 'center' }}>
        Be within {r}m of the gym for a one-tap check-in.
      </Text>
    </View>
  );
}

function LocatingHero() {
  const t = useTheme();
  return (
    <View
      style={{
        marginTop: spacing.xl,
        borderRadius: radius.xl,
        backgroundColor: t.tokens.bg.surface,
        borderWidth: 1,
        borderColor: t.tokens.border.subtle,
        padding: spacing.xl,
        paddingVertical: spacing.xxl,
        alignItems: 'center',
        gap: spacing.md,
      }}
    >
      <ActivityIndicator color={t.tokens.brand.accent} size="large" />
      <Text style={{ fontSize: 14, color: t.tokens.text.muted }}>Locating you…</Text>
    </View>
  );
}

function PermissionDeniedHero() {
  const t = useTheme();
  return (
    <View
      style={{
        marginTop: spacing.xl,
        borderRadius: radius.xl,
        backgroundColor: t.tokens.bg.warningSoft,
        borderWidth: 1,
        borderColor: t.tokens.border.subtle,
        padding: spacing.xl,
        alignItems: 'center',
      }}
    >
      <Icon name="lock" size={28} color={t.tokens.text.warning} />
      <Text
        style={{
          fontSize: 16,
          fontWeight: '700',
          color: t.tokens.text.primary,
          marginTop: spacing.md,
          textAlign: 'center',
        }}
      >
        Location off
      </Text>
      <Text
        style={{
          fontSize: 13,
          color: t.tokens.text.secondary,
          marginTop: 6,
          lineHeight: 19,
          textAlign: 'center',
        }}
      >
        Enable location in Settings to check in by walking up to the gym.
        You can still use manual or biometric check-in below.
      </Text>
    </View>
  );
}
