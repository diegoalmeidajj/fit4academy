import { useCallback, useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
  Pressable,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useRouter } from 'expo-router';

import { colors, radius, spacing, type as typeS } from '@/lib/theme';
import { apiGet } from '@/lib/api';

type Payment = {
  id: number;
  amount: number;
  status: string;
  method: string;
  reference: string;
  notes: string;
  payment_date: string;
  due_date: string | null;
};

const STATUS_COLOR: Record<string, string> = {
  completed: colors.green,
  paid: colors.green,
  pending: colors.warning,
  late: colors.warning,
  failed: colors.danger,
  refunded: colors.textMuted,
};

const STATUS_LABEL: Record<string, string> = {
  completed: 'Paid',
  paid: 'Paid',
  pending: 'Pending',
  late: 'Past due',
  failed: 'Failed',
  refunded: 'Refunded',
};

export default function PaymentsScreen() {
  const router = useRouter();
  const [items, setItems] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const r = await apiGet<{ items: Payment[] }>('/api/v1/me/payments');
    if (r.ok) setItems(r.data.items || []);
    setLoading(false);
    setRefreshing(false);
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));
  useEffect(() => { load(); }, [load]);

  const totalPaid = items
    .filter(p => ['paid', 'completed'].includes((p.status || '').toLowerCase()))
    .reduce((s, p) => s + (p.amount || 0), 0);
  const totalPending = items
    .filter(p => ['pending', 'late'].includes((p.status || '').toLowerCase()))
    .reduce((s, p) => s + (p.amount || 0), 0);

  return (
    <SafeAreaView style={styles.root}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} style={styles.backBtn}>
          <Text style={styles.backLabel}>← Back</Text>
        </Pressable>
        <Text style={styles.title}>Payments</Text>
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
        {/* Summary */}
        <View style={styles.summaryRow}>
          <View style={[styles.summaryCard, { borderColor: 'rgba(0,220,130,0.3)' }]}>
            <Text style={styles.summaryLabel}>Total paid</Text>
            <Text style={[styles.summaryValue, { color: colors.green }]}>
              ${totalPaid.toFixed(2)}
            </Text>
          </View>
          <View style={[styles.summaryCard, { borderColor: 'rgba(245,158,11,0.3)' }]}>
            <Text style={styles.summaryLabel}>Pending</Text>
            <Text style={[styles.summaryValue, { color: colors.warning }]}>
              ${totalPending.toFixed(2)}
            </Text>
          </View>
        </View>

        <View style={styles.infoBox}>
          <Text style={styles.infoText}>
            To update your card or address, tap "Request change" below — your coach
            will reach out, or you can pay directly when receiving a payment link.
          </Text>
        </View>

        <Text style={styles.section}>History</Text>

        {loading && items.length === 0 ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.green} size="large" />
          </View>
        ) : items.length === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyIcon}>💳</Text>
            <Text style={styles.emptyTitle}>No payments yet</Text>
          </View>
        ) : (
          items.map((p) => {
            const sLow = (p.status || '').toLowerCase();
            const color = STATUS_COLOR[sLow] || colors.textMuted;
            const label = STATUS_LABEL[sLow] || p.status || '—';
            return (
              <View key={p.id} style={styles.card}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.cardAmount}>${(p.amount || 0).toFixed(2)}</Text>
                  <Text style={styles.cardMeta}>
                    {p.payment_date}{p.method ? ` · ${p.method}` : ''}
                  </Text>
                  {!!p.notes && (
                    <Text style={styles.cardNotes} numberOfLines={2}>{p.notes}</Text>
                  )}
                </View>
                <View style={[styles.badge, { borderColor: color }]}>
                  <Text style={[styles.badgeLabel, { color }]}>{label}</Text>
                </View>
              </View>
            );
          })
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
  center: { paddingVertical: 60, alignItems: 'center' },

  summaryRow: { flexDirection: 'row', gap: spacing.md, marginBottom: spacing.md },
  summaryCard: {
    flex: 1,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: spacing.lg,
  },
  summaryLabel: { ...typeS.caption, color: colors.textMuted },
  summaryValue: { ...typeS.h1, marginTop: 4 },

  infoBox: {
    backgroundColor: 'rgba(34,211,238,0.06)',
    borderColor: 'rgba(34,211,238,0.2)',
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  infoText: { color: colors.greenLight, fontSize: 13, lineHeight: 19 },

  section: {
    ...typeS.caption,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: spacing.sm,
  },

  empty: { paddingVertical: 60, alignItems: 'center' },
  emptyIcon: { fontSize: 48, marginBottom: spacing.sm },
  emptyTitle: { ...typeS.body, color: colors.textMuted },

  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: 1,
    borderColor: colors.borderDark,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: 8,
  },
  cardAmount: { color: '#fff', fontSize: 17, fontWeight: '700' },
  cardMeta: { color: colors.textMuted, fontSize: 12, marginTop: 4 },
  cardNotes: { color: colors.textMuted, fontSize: 12, marginTop: 4, fontStyle: 'italic' },

  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.pill,
    borderWidth: 1.5,
  },
  badgeLabel: { fontSize: 11, fontWeight: '700' },
});
