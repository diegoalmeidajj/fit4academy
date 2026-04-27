import { useCallback, useEffect, useState } from 'react';
import {
  View, Text, ActivityIndicator, Alert, ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect } from 'expo-router';

import { useTheme, radius, spacing } from '@/lib/theme';
import { apiGet, apiPost } from '@/lib/api';
import {
  Coords, distanceMeters, getCurrentPosition, requestForegroundPermission,
} from '@/lib/geofence';
import { authenticate, biometricCapability } from '@/lib/biometric';
import { Card } from '@/components/Card';
import { Button } from '@/components/Button';

type GeofenceInfo = {
  academy_id: number; name: string; lat: number; lng: number; radius: number; configured: boolean;
};

type Status = 'idle' | 'requesting_perm' | 'locating' | 'ready' | 'submitting' | 'done' | 'error';

const ERR_MAP: Record<string, string> = {
  too_soon: 'You just checked in. Wait a minute and try again.',
  network_error: "Can't reach the server.",
  invalid_method: 'Invalid check-in method.',
};

export default function CheckinScreen() {
  const t = useTheme();
  const [geo, setGeo] = useState<GeofenceInfo | null>(null);
  const [pos, setPos] = useState<Coords | null>(null);
  const [permGranted, setPermGranted] = useState<boolean | null>(null);
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);
  const [bio, setBio] = useState({ available: false, label: '' });

  const distance = geo && pos ? distanceMeters({ lat: geo.lat, lng: geo.lng }, pos) : null;
  const insideRadius = distance != null && geo ? distance <= geo.radius : false;

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
      setTimeout(() => setStatus('ready'), 2000);
    }
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.tokens.bg.canvas }}>
      <ScrollView contentContainerStyle={{ padding: spacing.xl, paddingBottom: spacing.xxxl }}>
        <Text style={{ fontSize: 28, fontWeight: '800', color: t.tokens.text.primary, letterSpacing: -0.5 }}>
          Check in
        </Text>
        <Text style={{ ...t.type.body, color: t.tokens.text.muted, marginTop: 4, marginBottom: spacing.lg }}>
          {geo?.name || 'Your academy'}
        </Text>

        <Card style={{ marginBottom: spacing.md }}>
          {!geo?.configured ? (
            <Text style={{ ...t.type.body, color: t.tokens.text.warning, lineHeight: 22 }}>
              Your gym hasn't set its location yet. Ask staff to configure it.
            </Text>
          ) : permGranted === false ? (
            <Text style={{ ...t.type.body, color: t.tokens.text.warning, lineHeight: 22 }}>
              Location permission denied. Enable it in Settings to use geofence check-in.
              You can still check in manually below.
            </Text>
          ) : distance == null ? (
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <ActivityIndicator color={t.tokens.brand.accent} />
              <Text style={{ ...t.type.body, color: t.tokens.text.muted, marginLeft: 8 }}>
                Locating you…
              </Text>
            </View>
          ) : (
            <>
              <Text style={{ ...t.type.caption, color: t.tokens.text.muted }}>DISTANCE TO GYM</Text>
              <Text style={{
                fontSize: 56, fontWeight: '800', letterSpacing: -2, marginVertical: 6,
                color: insideRadius ? t.tokens.text.success : t.tokens.text.warning,
              }}>
                {Math.round(distance)} m
              </Text>
              <Text style={{ ...t.type.body, color: t.tokens.text.muted, lineHeight: 22 }}>
                {insideRadius
                  ? "You're at the gym — tap below to check in."
                  : `Be within ${geo.radius}m of the gym for geofence check-in.`}
              </Text>
            </>
          )}
        </Card>

        <View style={{ gap: spacing.sm, marginTop: spacing.md }}>
          <Button
            label={status === 'done' ? '✓ Checked in!' : '📍 Check in here'}
            onPress={() => submit('geofence')}
            disabled={!insideRadius}
            loading={status === 'submitting'}
            size="lg"
          />
          {bio.available && (
            <Button
              label={`Confirm with ${bio.label}`}
              onPress={() => submit('biometric')}
              disabled={status === 'submitting'}
              variant="secondary"
            />
          )}
          <Button
            label="Manual check-in"
            onPress={() => submit('manual')}
            disabled={status === 'submitting'}
            variant="ghost"
          />
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
