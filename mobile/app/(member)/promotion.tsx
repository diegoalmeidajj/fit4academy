import { useCallback, useEffect, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useRouter } from 'expo-router';

import { colors, radius, spacing, type as typeS, shadow } from '@/lib/theme';
import { apiGet, apiPost } from '@/lib/api';
import { useAuth } from '@/store/auth';

type ReqItem = {
  id: number;
  current_belt: string;
  current_stripes: number;
  requested_belt: string;
  requested_stripes: number;
  message: string;
  status: 'pending' | 'approved' | 'rejected';
  decision_note: string;
  created_at: string;
  decided_at: string | null;
};

const BELTS = ['White', 'Blue', 'Purple', 'Brown', 'Black'];

const STATUS_COLOR: Record<string, string> = {
  pending: colors.warning,
  approved: colors.green,
  rejected: colors.danger,
};

const ERR_MAP: Record<string, string> = {
  pending_request_exists: 'You already have a pending request. Wait for the coach to respond.',
  requested_belt_or_stripes_required: 'Pick a belt or number of stripes to request.',
};

export default function PromotionScreen() {
  const router = useRouter();
  const me = useAuth(s => s.me);
  const [items, setItems] = useState<ReqItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [requestedBelt, setRequestedBelt] = useState('');
  const [requestedStripes, setRequestedStripes] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    const r = await apiGet<{ items: ReqItem[] }>('/api/v1/me/promotion-requests');
    if (r.ok) setItems(r.data.items || []);
    setLoading(false);
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));
  useEffect(() => { load(); }, [load]);

  const hasPending = items.some(r => r.status === 'pending');

  async function submit() {
    if (submitting) return;
    setError(null);
    if (!requestedBelt && !requestedStripes) {
      setError(ERR_MAP.requested_belt_or_stripes_required);
      return;
    }
    setSubmitting(true);
    const stripesNum = requestedStripes ? parseInt(requestedStripes, 10) : 0;
    const r = await apiPost('/api/v1/me/promotion-requests', {
      requested_belt: requestedBelt,
      requested_stripes: isNaN(stripesNum) ? 0 : stripesNum,
      message,
    });
    setSubmitting(false);
    if (!r.ok) {
      setError(ERR_MAP[r.error || ''] || r.error || 'Could not submit. Try again.');
      return;
    }
    setRequestedBelt('');
    setRequestedStripes('');
    setMessage('');
    load();
  }

  const memberBelt = me?.type === 'member' ? me.belt : '';
  const memberStripes = me?.type === 'member' ? me.stripes : 0;

  return (
    <SafeAreaView style={styles.root}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView contentContainerStyle={styles.scroll}>
          <Pressable onPress={() => router.back()} style={styles.backBtn}>
            <Text style={styles.backLabel}>← Back</Text>
          </Pressable>
          <Text style={styles.title}>Request a promotion</Text>
          <Text style={styles.sub}>
            You're currently <Text style={{ color: colors.green, fontWeight: '700' }}>
            {memberBelt || 'unranked'}
            </Text>
            {memberStripes ? ` · ${memberStripes} stripes` : ''}.
          </Text>
          <Text style={styles.helper}>
            Your coach decides. Submit a request and they'll review it on their app.
          </Text>

          {hasPending ? (
            <View style={styles.warnBox}>
              <Text style={styles.warnText}>
                You have a pending request. Wait for your coach's decision before submitting another.
              </Text>
            </View>
          ) : (
            <>
              <Text style={styles.label}>Belt I'm requesting</Text>
              <View style={styles.beltRow}>
                {BELTS.map((b) => (
                  <Pressable
                    key={b}
                    style={[
                      styles.beltOpt,
                      requestedBelt === b && styles.beltOptActive,
                    ]}
                    onPress={() => setRequestedBelt(requestedBelt === b ? '' : b)}
                  >
                    <Text
                      style={[
                        styles.beltOptLabel,
                        requestedBelt === b && styles.beltOptLabelActive,
                      ]}
                    >
                      {b}
                    </Text>
                  </Pressable>
                ))}
              </View>

              <Text style={styles.label}>Stripes (optional)</Text>
              <TextInput
                style={styles.input}
                value={requestedStripes}
                onChangeText={setRequestedStripes}
                keyboardType="number-pad"
                placeholder="e.g. 4"
                placeholderTextColor={colors.textMuted}
                maxLength={1}
              />

              <Text style={styles.label}>Message to coach (optional)</Text>
              <TextInput
                style={[styles.input, { height: 90, textAlignVertical: 'top' }]}
                value={message}
                onChangeText={setMessage}
                placeholder="e.g. Been training 6 days a week, tapped Henrique on Saturday."
                placeholderTextColor={colors.textMuted}
                multiline
                maxLength={1000}
              />

              {error && <Text style={styles.error}>{error}</Text>}

              <Pressable
                style={[styles.cta, submitting && styles.ctaDisabled]}
                onPress={submit}
                disabled={submitting}
              >
                {submitting ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.ctaLabel}>Submit request</Text>
                )}
              </Pressable>
            </>
          )}

          <Text style={styles.section}>Your requests</Text>

          {loading && items.length === 0 ? (
            <View style={styles.center}>
              <ActivityIndicator color={colors.green} />
            </View>
          ) : items.length === 0 ? (
            <Text style={styles.empty}>No requests yet.</Text>
          ) : (
            items.map((it) => (
              <View key={it.id} style={styles.histCard}>
                <View style={styles.histHeader}>
                  <Text style={styles.histTitle}>
                    {it.requested_belt || 'Stripe up'}
                    {it.requested_stripes ? ` · ${it.requested_stripes} stripes` : ''}
                  </Text>
                  <View
                    style={[
                      styles.statusBadge,
                      { borderColor: STATUS_COLOR[it.status] || colors.textMuted },
                    ]}
                  >
                    <Text
                      style={[
                        styles.statusLabel,
                        { color: STATUS_COLOR[it.status] || colors.textMuted },
                      ]}
                    >
                      {it.status.toUpperCase()}
                    </Text>
                  </View>
                </View>
                <Text style={styles.histMeta}>Sent {it.created_at.slice(0, 10)}</Text>
                {!!it.message && (
                  <Text style={styles.histBody}>"{it.message}"</Text>
                )}
                {!!it.decision_note && (
                  <View style={styles.decisionBox}>
                    <Text style={styles.decisionLabel}>Coach said:</Text>
                    <Text style={styles.decisionText}>{it.decision_note}</Text>
                  </View>
                )}
              </View>
            ))
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bgDeep },
  scroll: { padding: spacing.xl, paddingBottom: spacing.xxl },
  center: { padding: spacing.lg, alignItems: 'center' },

  backBtn: { marginBottom: 8 },
  backLabel: { color: colors.green, fontWeight: '600' },
  title: { ...typeS.h1, color: '#fff' },
  sub: { ...typeS.body, color: colors.textMuted, marginTop: 6 },
  helper: { ...typeS.body, color: colors.textMuted, marginTop: 4, marginBottom: spacing.lg, lineHeight: 20 },

  warnBox: {
    backgroundColor: 'rgba(245,158,11,0.08)',
    borderColor: 'rgba(245,158,11,0.3)',
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  warnText: { color: colors.warning, fontSize: 13, lineHeight: 19 },

  label: {
    ...typeS.caption,
    color: colors.textMuted,
    marginBottom: 6,
    marginTop: spacing.md,
  },
  beltRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  beltOpt: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: radius.pill,
    borderWidth: 1.5,
    borderColor: colors.borderDark,
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  beltOptActive: {
    borderColor: colors.green,
    backgroundColor: 'rgba(0,220,130,0.1)',
  },
  beltOptLabel: { color: colors.textMuted, fontWeight: '600', fontSize: 13 },
  beltOptLabelActive: { color: colors.green },

  input: {
    color: '#fff',
    fontSize: 15,
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderWidth: 1.5,
    borderColor: colors.borderDark,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderRadius: radius.md,
  },

  error: { color: colors.danger, fontSize: 13, marginTop: spacing.md, textAlign: 'center' },

  cta: {
    backgroundColor: colors.green,
    paddingVertical: 14,
    borderRadius: radius.md,
    alignItems: 'center',
    marginTop: spacing.lg,
    ...shadow.cta,
  },
  ctaDisabled: { opacity: 0.5 },
  ctaLabel: { color: '#fff', fontWeight: '700', fontSize: 15 },

  section: {
    ...typeS.caption,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
  },
  empty: {
    color: colors.textMuted,
    textAlign: 'center',
    paddingVertical: spacing.xl,
    fontStyle: 'italic',
  },

  histCard: {
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: 1,
    borderColor: colors.borderDark,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  histHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  histTitle: { color: '#fff', fontWeight: '700', fontSize: 14, flex: 1 },
  histMeta: { color: colors.textMuted, fontSize: 11, marginTop: 4 },
  histBody: { color: '#fff', fontStyle: 'italic', marginTop: 6, fontSize: 13, lineHeight: 18 },

  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: radius.pill,
    borderWidth: 1.5,
  },
  statusLabel: { fontWeight: '700', fontSize: 10, letterSpacing: 0.5 },

  decisionBox: {
    backgroundColor: 'rgba(0,220,130,0.06)',
    borderRadius: radius.sm,
    padding: 10,
    marginTop: 8,
  },
  decisionLabel: { color: colors.green, fontSize: 11, fontWeight: '700', marginBottom: 2 },
  decisionText: { color: '#fff', fontSize: 13, lineHeight: 18 },
});
