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
import { Icon, IconName } from '@/components/Icon';
import { InstallPrompt } from '@/components/InstallPrompt';

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
  academy: { id: number; name: string; primary_color: string } | null;
  membership: {
    state: 'active' | 'late' | 'expired' | 'unknown';
    days_late: number;
    next_due: string | null;
  };
  last_checkin: { id: number; created_at: string; class_name: string; method: string } | null;
  total_checkins: number;
  unread_chat_count?: number;
  last_unread_chat?: { body: string; created_at: string } | null;
};

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 5) return 'Burning the midnight oil';
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

function BeltGraphic({ color, stripes }: { color: string; stripes: number }) {
  // A fabric-like belt rendered as a stack of bars with the cloth color, plus
  // tape "stripes" on the right end like real BJJ ranks. Visually communicates
  // achievement far better than a tiny color swatch.
  const t = useTheme();
  const beltColor = color || '#ffffff';
  const isWhite = beltColor.toLowerCase() === '#ffffff' || beltColor.toLowerCase() === '#fff';
  return (
    <View
      style={{
        width: '100%',
        height: 56,
        borderRadius: 10,
        backgroundColor: beltColor,
        borderWidth: isWhite ? 1 : 0,
        borderColor: 'rgba(0,0,0,0.12)',
        flexDirection: 'row',
        overflow: 'hidden',
        shadowColor: '#000',
        shadowOpacity: t.mode === 'dark' ? 0.5 : 0.12,
        shadowRadius: 12,
        shadowOffset: { width: 0, height: 6 },
        elevation: 4,
      }}
    >
      <View style={{ flex: 1 }} />
      {/* Black tape end of the belt where stripes sit */}
      <View
        style={{
          width: 88,
          height: '100%',
          backgroundColor: '#0f1419',
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'flex-start',
          paddingLeft: 10,
          gap: 6,
        }}
      >
        {Array.from({ length: 4 }).map((_, i) => (
          <View
            key={i}
            style={{
              width: 4,
              height: 38,
              borderRadius: 2,
              backgroundColor: i < stripes ? '#ffffff' : 'rgba(255,255,255,0.10)',
            }}
          />
        ))}
      </View>
    </View>
  );
}

type QuickLink = { icon: IconName; label: string; sublabel: string; route: string; tone: 'accent' | 'neutral' };

const QUICK_LINKS: QuickLink[] = [
  { icon: 'card', label: 'Payments', sublabel: 'View invoices & pay', route: '/(member)/payments', tone: 'accent' },
  { icon: 'calendar', label: 'Schedule', sublabel: 'Classes this week', route: '/(member)/schedule', tone: 'neutral' },
  { icon: 'belt', label: 'Promotion', sublabel: 'Track your progress', route: '/(member)/promotion', tone: 'neutral' },
  { icon: 'message', label: 'Coach chat', sublabel: 'Message your coach', route: '/(member)/chat', tone: 'neutral' },
];

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

  const firstName = data?.member.first_name || me.first_name || 'athlete';
  const beltLabel = data?.member.belt || 'White';

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.tokens.bg.canvas }}>
      <ScrollView
        contentContainerStyle={{ paddingBottom: spacing.xxxl + 40 }}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); load(); }}
            tintColor={t.tokens.brand.accent}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Header — greeting + avatar + bell */}
        <View
          style={{
            paddingHorizontal: spacing.xl,
            paddingTop: spacing.lg,
            paddingBottom: spacing.md,
            flexDirection: 'row',
            alignItems: 'center',
            gap: spacing.md,
          }}
        >
          <Avatar initials={initials} size={44} />
          <View style={{ flex: 1 }}>
            <Text
              style={{
                fontSize: 12.5,
                fontWeight: '500',
                color: t.tokens.text.muted,
                letterSpacing: 0.1,
              }}
            >
              {getGreeting()}
            </Text>
            <Text
              style={{
                fontSize: 19,
                fontWeight: '700',
                color: t.tokens.text.primary,
                letterSpacing: -0.4,
                marginTop: 1,
              }}
            >
              {firstName}
            </Text>
          </View>
          <Pressable
            onPress={() => router.push('/(member)/chat' as any)}
            style={({ pressed }) => ({
              width: 40, height: 40, borderRadius: 20,
              backgroundColor: t.tokens.bg.surfaceAlt,
              alignItems: 'center', justifyContent: 'center',
              opacity: pressed ? 0.7 : 1,
            })}
            hitSlop={8}
          >
            <Icon name="bell" size={20} color={t.tokens.text.secondary} />
            {!!data?.unread_chat_count && data.unread_chat_count > 0 && (
              <View
                style={{
                  position: 'absolute',
                  top: 6,
                  right: 6,
                  width: 10,
                  height: 10,
                  borderRadius: 5,
                  backgroundColor: '#f59e0b',
                  borderWidth: 2,
                  borderColor: t.tokens.bg.canvas,
                }}
              />
            )}
          </Pressable>
        </View>

        {/* Install / push opt-in prompt — only renders on web outside standalone PWA */}
        <InstallPrompt />

        {/* Unread chat alert — shows when staff sent a message the member hasn't read.
            Tapping sends them to chat where the read marker auto-fires. */}
        {!!data?.unread_chat_count && data.unread_chat_count > 0 && (
          <View style={{ paddingHorizontal: spacing.xl, marginTop: spacing.md }}>
            <Pressable
              onPress={() => router.push('/(member)/chat' as any)}
              style={({ pressed }) => ({
                borderRadius: radius.lg,
                padding: spacing.lg,
                backgroundColor: 'rgba(245,158,11,0.10)',
                borderWidth: 1,
                borderColor: 'rgba(245,158,11,0.45)',
                flexDirection: 'row',
                alignItems: 'center',
                gap: spacing.md,
                opacity: pressed ? 0.85 : 1,
              })}
            >
              <View
                style={{
                  width: 40, height: 40, borderRadius: 20,
                  backgroundColor: '#f59e0b',
                  alignItems: 'center', justifyContent: 'center',
                  shadowColor: '#f59e0b',
                  shadowOpacity: 0.4,
                  shadowRadius: 12,
                  shadowOffset: { width: 0, height: 4 },
                  elevation: 4,
                }}
              >
                <Icon name="message" size={20} color="#0f172a" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={{ fontSize: 13, fontWeight: '700', color: '#f59e0b', letterSpacing: 0.3 }}>
                  {data.unread_chat_count} NEW MESSAGE{data.unread_chat_count > 1 ? 'S' : ''}
                </Text>
                <Text
                  numberOfLines={2}
                  style={{
                    fontSize: 14,
                    color: t.tokens.text.primary,
                    marginTop: 2,
                    lineHeight: 19,
                  }}
                >
                  {data.last_unread_chat?.body || 'Tap to open the chat'}
                </Text>
              </View>
              <Icon name="chevron-right" size={20} color="#f59e0b" />
            </Pressable>
          </View>
        )}

        {/* Hero rank card */}
        <View style={{ paddingHorizontal: spacing.xl, marginTop: spacing.sm }}>
          <Card variant="elevated" padded={false} style={{ overflow: 'hidden' }}>
            <View style={{ padding: spacing.xl, paddingBottom: spacing.lg }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: spacing.sm }}>
                <Text style={{ ...t.type.overline, color: t.tokens.text.muted }}>
                  CURRENT RANK
                </Text>
                <Badge label={ms?.state === 'active' ? 'Active' : (ms?.state || 'unknown')} tone={msTone} />
              </View>
              <Text
                style={{
                  fontSize: 30,
                  fontWeight: '800',
                  color: t.tokens.text.primary,
                  letterSpacing: -0.8,
                  marginTop: 6,
                }}
              >
                {beltLabel}
                <Text style={{ color: t.tokens.text.muted, fontWeight: '500' }}> belt</Text>
              </Text>
              <Text style={{ fontSize: 13, color: t.tokens.text.muted, marginTop: 4 }}>
                {data?.member.stripes ? `${data.member.stripes} stripe${data.member.stripes > 1 ? 's' : ''}` : 'No stripes yet — keep training.'}
              </Text>
            </View>
            <View style={{ paddingHorizontal: spacing.xl, paddingBottom: spacing.xl }}>
              <BeltGraphic color={data?.member.belt_color || '#ffffff'} stripes={data?.member.stripes || 0} />
            </View>
          </Card>
        </View>

        {/* Stats row */}
        <View style={{ flexDirection: 'row', gap: spacing.md, paddingHorizontal: spacing.xl, marginTop: spacing.md }}>
          <View
            style={{
              flex: 1,
              backgroundColor: t.tokens.bg.accentSoft,
              borderRadius: radius.lg,
              borderWidth: 1,
              borderColor: t.tokens.border.subtle,
              padding: spacing.lg,
            }}
          >
            <Text style={{ fontSize: 11, fontWeight: '700', color: t.tokens.brand.accent, letterSpacing: 0.5 }}>
              CHECK-INS
            </Text>
            <Text
              style={{
                fontSize: 36,
                fontWeight: '800',
                color: t.tokens.text.primary,
                letterSpacing: -1.2,
                marginTop: 6,
              }}
            >
              {data?.total_checkins ?? 0}
            </Text>
            <Text style={{ fontSize: 12, color: t.tokens.text.muted, marginTop: 2 }}>
              all time
            </Text>
          </View>
          <View
            style={{
              flex: 1,
              backgroundColor: t.tokens.bg.surface,
              borderRadius: radius.lg,
              borderWidth: 1,
              borderColor: t.tokens.border.subtle,
              padding: spacing.lg,
            }}
          >
            <Text style={{ fontSize: 11, fontWeight: '700', color: t.tokens.text.muted, letterSpacing: 0.5 }}>
              LAST CLASS
            </Text>
            <Text
              style={{
                fontSize: 22,
                fontWeight: '800',
                color: t.tokens.text.primary,
                letterSpacing: -0.6,
                marginTop: 6,
              }}
              numberOfLines={1}
            >
              {data?.last_checkin ? data.last_checkin.created_at.slice(5, 10) : '—'}
            </Text>
            <Text style={{ fontSize: 12, color: t.tokens.text.muted, marginTop: 2 }} numberOfLines={1}>
              {data?.last_checkin?.class_name || 'no recent class'}
            </Text>
          </View>
        </View>

        {/* Membership status (only when actionable) */}
        {ms && ms.state !== 'active' && (
          <View style={{ paddingHorizontal: spacing.xl, marginTop: spacing.md }}>
            <Pressable onPress={() => router.push('/(member)/payments' as any)}>
              <View
                style={{
                  borderRadius: radius.lg,
                  padding: spacing.lg,
                  backgroundColor:
                    ms.state === 'late' ? t.tokens.bg.warningSoft :
                    ms.state === 'expired' ? t.tokens.bg.dangerSoft :
                    t.tokens.bg.surface,
                  borderWidth: 1,
                  borderColor: t.tokens.border.subtle,
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: spacing.md,
                }}
              >
                <View
                  style={{
                    width: 36, height: 36, borderRadius: 18,
                    backgroundColor:
                      ms.state === 'expired' ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)',
                    alignItems: 'center', justifyContent: 'center',
                  }}
                >
                  <Icon
                    name="card"
                    size={18}
                    color={ms.state === 'expired' ? '#ef4444' : '#f59e0b'}
                  />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={{ fontSize: 14, fontWeight: '700', color: t.tokens.text.primary }}>
                    {msLabel}
                  </Text>
                  <Text style={{ fontSize: 12, color: t.tokens.text.muted, marginTop: 2 }}>
                    Tap to settle your balance
                  </Text>
                </View>
                <Icon name="chevron-right" size={20} color={t.tokens.text.muted} />
              </View>
            </Pressable>
          </View>
        )}

        {/* Quick links */}
        <View style={{ paddingHorizontal: spacing.xl, marginTop: spacing.xl }}>
          <Text
            style={{
              ...t.type.overline,
              color: t.tokens.text.muted,
              marginBottom: spacing.md,
            }}
          >
            QUICK ACTIONS
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
            {QUICK_LINKS.map((link, i) => {
              const unread = link.icon === 'message' ? (data?.unread_chat_count || 0) : 0;
              return (
                <Pressable
                  key={link.label}
                  onPress={() => router.push(link.route as any)}
                  style={({ pressed }) => ({
                    flexDirection: 'row',
                    alignItems: 'center',
                    gap: spacing.md,
                    paddingVertical: 14,
                    paddingHorizontal: spacing.lg,
                    borderTopWidth: i === 0 ? 0 : 0.5,
                    borderTopColor: t.tokens.border.subtle,
                    backgroundColor: pressed ? t.tokens.bg.surfaceAlt : 'transparent',
                  })}
                >
                  <View
                    style={{
                      width: 36, height: 36, borderRadius: 10,
                      backgroundColor: link.tone === 'accent' ? t.tokens.bg.accentSoft : t.tokens.bg.surfaceAlt,
                      alignItems: 'center', justifyContent: 'center',
                    }}
                  >
                    <Icon
                      name={link.icon}
                      size={18}
                      color={link.tone === 'accent' ? t.tokens.brand.accent : t.tokens.text.secondary}
                    />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={{ fontSize: 15, fontWeight: '600', color: t.tokens.text.primary }}>
                      {link.label}
                    </Text>
                    <Text style={{ fontSize: 12, color: t.tokens.text.muted, marginTop: 1 }}>
                      {link.sublabel}
                    </Text>
                  </View>
                  {unread > 0 && (
                    <View
                      style={{
                        backgroundColor: '#f59e0b',
                        minWidth: 22,
                        height: 22,
                        borderRadius: 11,
                        paddingHorizontal: 7,
                        alignItems: 'center',
                        justifyContent: 'center',
                        marginRight: 6,
                        shadowColor: '#f59e0b',
                        shadowOpacity: 0.5,
                        shadowRadius: 8,
                        shadowOffset: { width: 0, height: 2 },
                        elevation: 3,
                      }}
                    >
                      <Text style={{ fontSize: 12, fontWeight: '800', color: '#0f172a' }}>
                        {unread > 99 ? '99+' : unread}
                      </Text>
                    </View>
                  )}
                  <Icon name="chevron-right" size={18} color={t.tokens.text.disabled} />
                </Pressable>
              );
            })}
          </View>
        </View>

        {/* Academy footer */}
        <View style={{ alignItems: 'center', marginTop: spacing.xl }}>
          <Text style={{ fontSize: 11, fontWeight: '600', color: t.tokens.text.muted, letterSpacing: 0.4 }}>
            {(data?.academy?.name || me.academy?.name || 'Your academy').toUpperCase()}
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
