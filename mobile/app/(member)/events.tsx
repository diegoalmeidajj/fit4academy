import { useCallback, useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
  Pressable,
  Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useRouter } from 'expo-router';

import { colors, radius, spacing, type as typeS } from '@/lib/theme';
import { apiGet } from '@/lib/api';

type EventItem = {
  id: number;
  title: string;
  description: string;
  event_date: string;
  event_time: string;
  location: string;
  photo: string;
  event_type: string;
  price: number;
  landing_url: string;
};

export default function EventsScreen() {
  const router = useRouter();
  const [items, setItems] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const r = await apiGet<{ items: EventItem[] }>('/api/v1/me/events');
    if (r.ok) setItems(r.data.items || []);
    setLoading(false);
    setRefreshing(false);
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));
  useEffect(() => { load(); }, [load]);

  return (
    <SafeAreaView style={styles.root}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} style={styles.backBtn}>
          <Text style={styles.backLabel}>← Back</Text>
        </Pressable>
        <Text style={styles.title}>Events & Competitions</Text>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); load(); }}
            tintColor={colors.green}
          />
        }
      >
        {loading && items.length === 0 ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.green} size="large" />
          </View>
        ) : items.length === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyIcon}>🏆</Text>
            <Text style={styles.emptyTitle}>No upcoming events</Text>
            <Text style={styles.emptyText}>
              Your gym hasn't posted any competitions or events yet. Check back soon.
            </Text>
          </View>
        ) : (
          items.map((e) => (
            <View key={e.id} style={styles.card}>
              <View style={styles.dateBadge}>
                <Text style={styles.dateMonth}>
                  {e.event_date ? e.event_date.slice(5, 7) : '--'}
                </Text>
                <Text style={styles.dateDay}>
                  {e.event_date ? e.event_date.slice(8, 10) : '--'}
                </Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.cardTitle}>{e.title}</Text>
                {!!e.location && (
                  <Text style={styles.cardMeta}>📍 {e.location}</Text>
                )}
                {!!e.event_time && (
                  <Text style={styles.cardMeta}>🕐 {e.event_time}</Text>
                )}
                {e.price > 0 && (
                  <Text style={styles.cardPrice}>${e.price.toFixed(2)}</Text>
                )}
                {!!e.description && (
                  <Text style={styles.cardDesc} numberOfLines={3}>
                    {e.description}
                  </Text>
                )}
                {!!e.landing_url && (
                  <Pressable
                    style={styles.cta}
                    onPress={() => {
                      const url = e.landing_url.startsWith('http')
                        ? e.landing_url
                        : window.location?.origin
                        ? window.location.origin + e.landing_url
                        : e.landing_url;
                      Linking.openURL(url);
                    }}
                  >
                    <Text style={styles.ctaLabel}>View details →</Text>
                  </Pressable>
                )}
              </View>
            </View>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bgDeep },
  header: { padding: spacing.xl, paddingBottom: spacing.md },
  backBtn: { marginBottom: 8 },
  backLabel: { color: colors.green, fontWeight: '600' },
  title: { ...typeS.h1, color: '#fff' },
  scroll: { paddingHorizontal: spacing.xl, paddingBottom: spacing.xxl },
  center: { paddingVertical: 80, alignItems: 'center' },

  empty: { paddingVertical: 80, alignItems: 'center' },
  emptyIcon: { fontSize: 56, marginBottom: spacing.md },
  emptyTitle: { ...typeS.h2, color: '#fff', marginBottom: 6 },
  emptyText: {
    ...typeS.body,
    color: colors.textMuted,
    textAlign: 'center',
    paddingHorizontal: spacing.xl,
  },

  card: {
    flexDirection: 'row',
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: 1,
    borderColor: colors.borderDark,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
    gap: spacing.md,
  },
  dateBadge: {
    width: 56,
    backgroundColor: 'rgba(0,220,130,0.1)',
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.sm,
  },
  dateMonth: { color: colors.green, fontSize: 11, fontWeight: '700', letterSpacing: 0.5 },
  dateDay: { color: colors.green, fontSize: 24, fontWeight: '800' },

  cardTitle: { color: '#fff', fontSize: 16, fontWeight: '700' },
  cardMeta: { color: colors.textMuted, fontSize: 12, marginTop: 4 },
  cardDesc: { color: colors.textMuted, fontSize: 13, marginTop: 6, lineHeight: 18 },
  cardPrice: {
    color: colors.green,
    fontSize: 14,
    fontWeight: '700',
    marginTop: 4,
  },
  cta: { marginTop: spacing.sm, alignSelf: 'flex-start' },
  ctaLabel: { color: colors.green, fontWeight: '700' },
});
