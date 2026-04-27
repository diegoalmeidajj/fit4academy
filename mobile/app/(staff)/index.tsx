import { View, Text, ScrollView, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useTheme, radius, spacing } from '@/lib/theme';
import { useAuth } from '@/store/auth';
import { Card } from '@/components/Card';
import { Avatar } from '@/components/Avatar';
import { Button } from '@/components/Button';

export default function StaffHome() {
  const t = useTheme();
  const me = useAuth(s => s.me);
  const logout = useAuth(s => s.logout);

  if (!me || me.type !== 'staff') return null;

  const initials = (me.name || me.username || 'F4').slice(0, 2).toUpperCase();

  function openAdmin() {
    const path = window?.location?.origin ? '/notifications' : '';
    if (typeof window !== 'undefined' && window.location) {
      window.location.href = '/notifications';
      return;
    }
    Linking.openURL('http://localhost:8080/notifications');
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.tokens.bg.canvas }}>
      <ScrollView contentContainerStyle={{ padding: spacing.xl, paddingBottom: spacing.xxxl }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: spacing.xl, gap: spacing.md }}>
          <Avatar initials={initials} size={56} />
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: 22, fontWeight: '700', color: t.tokens.text.primary, letterSpacing: -0.4 }}>
              Hi, <Text style={{ color: t.tokens.brand.accent }}>{me.name || me.username}</Text>.
            </Text>
            <Text style={{ ...t.type.body, color: t.tokens.text.muted, marginTop: 2 }}>
              {me.academy?.name || 'Your academy'} · {me.role}
            </Text>
          </View>
        </View>

        <Card variant="tinted" style={{ marginBottom: spacing.lg }}>
          <Text style={{ ...t.type.h3, color: t.tokens.text.primary, marginBottom: 8 }}>
            👋 Member messages and promotion requests now arrive in your admin web Inbox
          </Text>
          <Text style={{ ...t.type.body, color: t.tokens.text.secondary, lineHeight: 22, marginBottom: spacing.md }}>
            Open <Text style={{ fontWeight: '700', color: t.tokens.text.accent }}>/notifications</Text> on
            the admin web to approve promotions, reply to chat, and see everything in one place.
          </Text>
          <Button label="Open Inbox →" onPress={openAdmin} fullWidth={false} />
        </Card>

        <Card>
          <Text style={{ ...t.type.h3, color: t.tokens.text.primary, marginBottom: 6 }}>
            Mobile staff console
          </Text>
          <Text style={{ ...t.type.body, color: t.tokens.text.muted, lineHeight: 22 }}>
            Coming next: today's KPIs, members list & search, quick check-in, manual payment.
            For now, use the full web admin for management.
          </Text>
        </Card>

        <View style={{ marginTop: spacing.xl }}>
          <Button label="Sign out" variant="ghost" onPress={logout} />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
