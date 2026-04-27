import { useCallback, useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
  Pressable,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useRouter } from 'expo-router';

import { useTheme, radius, spacing } from '@/lib/theme';
import { useAuth } from '@/store/auth';
import { apiGet } from '@/lib/api';
import { Card } from '@/components/Card';
import { Avatar } from '@/components/Avatar';
import { Badge } from '@/components/Badge';

type Dashboard = {
  member: {
    id: number;
    first_name: string;
    last_name: string;
    photo_url: string;
    belt: string;
    belt_color: string;
    stripes: number;
    email: string;
    phone: string;
  };
  academy: {
    id: number;
    name: string;
    primary_color: string;
  } | null;
  membership: {
    state: 'active' | 'late' | 'expired' | 'unknown';
    days_late: number;
    next_due: string | null;
  };
  last_checkin: { id: number; created_at: string; class_name: string; method: string } | null;
  total_checkins: number;
};

export default function MemberHome() {
  const t = useTheme();
  const me = useAuth(s => s.me);
  const router = useRouter();
  const [data, setData] = useState<Dashboard | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const r = await apiGet<Dashboard>('/api/v1/me/dashboard');
    if (r.ok) setData(r.data);
    setLoading(false);
    setRefreshing(false);
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));
  useEffect(() => { load(); }, [load]);

  if (!me || me.type !== 'member') return null;

  if (loading && !data) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: t.tokens.bg.canvas, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color={t.tokens.brand.accent} size="large" />
      </SafeAreaView>
    );
  }

  const initials = ((data?.member.first_name?.[0] || me.first_name?.[0] || '') +
    (data?.member.last_name?.[0] || me.last_name?.[0] || '')).toUpperCase() || 'F4';

  const ms = data?.membership;
  const msLabel = !ms ? '—'
    : ms.state === 'active' ? 'In good standing'
    : ms.state === 'late' ? `${ms.days_late} day${ms.days_late > 1 ? 's' : ''} late`
    : ms.state === 'expired' ? 'Expired' : 'Unknown';
  const msTone: 'success' | 'warning' | 'danger' | 'neutral' =
    ms?.state === 'active' ? 'success'
    : ms?.state === 'late' ? 'warning'
    : ms?.state === 'expired' ? 'danger' : 'neutral';

  const QUICK_LINKS = [
    { emoji: '💳', label: 'Payments', route: '/(member)/payments' },
    { emoji: '🏆', label: 'Events', route: '/(member)/events' },
    { emoji: '🥋', label: 'Promotion', route: '/(member)/promotion' },
    { emoji: '💬', label: 'Coach chat', route: '/(member)/chat' },
  ];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.tokens.bg.canvas }}>
      <ScrollView
        contentContainerStyle={{ padding: spacing.xl, paddingBottom: spacing.xxxl }}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); load(); }}
            tintColor={t.tokens.brand.accent}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Greeting */}
        <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: spacing.xl, gap: spacing.md }}>
          <Avatar initials={initials} size={56} />
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: 22, fontWeight: '700', color: t.tokens.text.primary, letterSpacing: -0.4 }}>
              Hello, <Text style={{ color: t.tokens.brand.accent }}>{data?.member.first_name || me.first_name || 'athlete'}</Text>.
            </Text>
            <Text style={{ ...t.type.body, color: t.tokens.text.muted, marginTop: 2 }}>
              {data?.academy?.name || me.academy?.name || 'Your academy'}
            </Text>
          </View>
        </View>

        {/* Belt card */}
        <Card style={{ marginBottom: spacing.md }}>
          <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginBottom: 10 }}>CURRENT RANK</Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.md }}>
            <View style={{
              width: 60, height: 16, borderRadius: 4,
              backgroundColor: data?.member.belt_color || '#fff',
              borderWidth: 1, borderColor: 'rgba(0,0,0,0.2)',
            }} />
            <View style={{ flex: 1 }}>
              <Text style={{ ...t.type.h3, color: t.tokens.text.primary }}>
                {data?.member.belt || 'White'} belt
              </Text>
              {!!data?.member.stripes && (
                <Text style={{ ...t.type.body, color: t.tokens.text.muted, marginTop: 4 }}>
                  {data.member.stripes} stripe{data.member.stripes > 1 ? 's' : ''}
                </Text>
              )}
            </View>
          </View>
        </Card>

        {/* Membership card */}
        <Card style={{ marginBottom: spacing.md }}>
          <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginBottom: 10 }}>MEMBERSHIP</Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
            <Text style={{ ...t.type.h3, color: t.tokens.text.primary, flex: 1 }}>{msLabel}</Text>
            <Badge label={ms?.state || 'unknown'} tone={msTone} />
          </View>
          {ms?.next_due && (
            <Text style={{ ...t.type.body, color: t.tokens.text.muted, marginTop: 8 }}>
              Next due: {ms.next_due}
            </Text>
          )}
        </Card>

        {/* Stats */}
        <View style={{ flexDirection: 'row', gap: spacing.md, marginBottom: spacing.md }}>
          <Card style={{ flex: 1 }}>
            <Text style={{ fontSize: 32, fontWeight: '800', color: t.tokens.brand.accent, letterSpacing: -1 }}>
              {data?.total_checkins ?? 0}
            </Text>
            <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginTop: 4 }}>TOTAL CHECK-INS</Text>
          </Card>
          <Card style={{ flex: 1 }}>
            <Text style={{ fontSize: 24, fontWeight: '800', color: t.tokens.text.primary, letterSpacing: -0.5 }}>
              {data?.last_checkin ? data.last_checkin.created_at.slice(5, 10) : '—'}
            </Text>
            <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginTop: 4 }}>LAST CHECK-IN</Text>
          </Card>
        </View>

        {/* Quick links */}
        <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginTop: spacing.lg, marginBottom: spacing.sm, textTransform: 'uppercase', letterSpacing: 0.6 }}>
          Quick actions
        </Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md }}>
          {QUICK_LINKS.map((link) => (
            <Card
              key={link.label}
              onPress={() => router.push(link.route as any)}
              style={{ flexBasis: '47%', flexGrow: 1 }}
            >
              <Text style={{ fontSize: 28, marginBottom: 8 }}>{link.emoji}</Text>
              <Text style={{ ...t.type.bodyMedium, color: t.tokens.text.primary, fontSize: 13 }}>
                {link.label}
              </Text>
            </Card>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
