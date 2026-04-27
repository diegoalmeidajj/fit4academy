import { useEffect } from 'react';
import { ActivityIndicator, View, StyleSheet } from 'react-native';
import { Slot, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { useAuth } from '@/store/auth';
import { useThemeMode } from '@/store/themeMode';
import { useTheme } from '@/lib/theme';

function AuthGate() {
  const t = useTheme();
  const status = useAuth(s => s.status);
  const me = useAuth(s => s.me);
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    if (status === 'booting') return;

    const inAuthGroup = segments[0] === '(auth)';
    const inMemberGroup = segments[0] === '(member)';
    const inStaffGroup = segments[0] === '(staff)';

    if (status === 'anonymous' && !inAuthGroup) {
      router.replace('/(auth)/login');
      return;
    }
    if (status === 'authenticated' && me?.type === 'member' && !inMemberGroup) {
      router.replace('/(member)');
      return;
    }
    if (status === 'authenticated' && me?.type === 'staff' && !inStaffGroup) {
      router.replace('/(staff)');
      return;
    }
  }, [status, me, segments, router]);

  if (status === 'booting') {
    return (
      <View style={[styles.boot, { backgroundColor: t.tokens.bg.canvas }]}>
        <ActivityIndicator color={t.tokens.brand.accent} size="large" />
      </View>
    );
  }
  return <Slot />;
}

export default function RootLayout() {
  const bootstrap = useAuth(s => s.bootstrap);
  const hydrateTheme = useThemeMode(s => s.hydrate);
  const themeMode = useThemeMode(s => s.mode);
  const t = useTheme();

  useEffect(() => {
    hydrateTheme();
    bootstrap();
  }, [bootstrap, hydrateTheme]);

  return (
    <>
      <StatusBar style={t.mode === 'light' ? 'dark' : 'light'} />
      <AuthGate />
    </>
  );
}

const styles = StyleSheet.create({
  boot: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
