import { useCallback, useEffect, useMemo, useState } from 'react';
import { View, Text, ScrollView, RefreshControl, Pressable, Linking, Alert, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Stack, router } from 'expo-router';

import { apiGet, apiPatch } from '@/lib/api';
import { useTheme, radius, spacing } from '@/lib/theme';
import { useAuth } from '@/store/auth';
import { Card } from '@/components/Card';
import { Badge } from '@/components/Badge';
import { Button } from '@/components/Button';

type Lead = {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  source: string;
  status: 'new' | 'contacted' | 'qualified' | 'converted' | 'lost';
  interested_in: string;
  previous_experience: string;
  notes: string;
  archived: boolean;
  created_at: string;
  updated_at: string;
};

type LeadsResponse = {
  items: Lead[];
  counts: { new: number; contacted: number; qualified: number; converted: number; lost: number; total: number };
};

const STATUS_FILTERS: Array<{ key: '' | Lead['status']; label: string }> = [
  { key: '', label: 'All' },
  { key: 'new', label: 'New' },
  { key: 'contacted', label: 'Contacted' },
  { key: 'qualified', label: 'Qualified' },
  { key: 'converted', label: 'Converted' },
];

function timeAgo(iso: string): string {
  if (!iso) return '';
  const t = new Date(iso.replace(' ', 'T') + 'Z').getTime();
  if (Number.isNaN(t)) return iso.slice(0, 10);
  const diff = Math.max(0, Date.now() - t);
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  return iso.slice(0, 10);
}

function statusTone(status: Lead['status']): 'info' | 'warning' | 'accent' | 'success' | 'neutral' {
  switch (status) {
    case 'new': return 'warning';
    case 'contacted': return 'info';
    case 'qualified': return 'accent';
    case 'converted': return 'success';
    case 'lost': return 'neutral';
    default: return 'neutral';
  }
}

export default function StaffLeads() {
  const t = useTheme();
  const me = useAuth(s => s.me);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [counts, setCounts] = useState<LeadsResponse['counts'] | null>(null);
  const [filter, setFilter] = useState<'' | Lead['status']>('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [openId, setOpenId] = useState<number | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const academyId = me && me.type === 'staff' ? me.academy?.id : undefined;
  const shareUrl = useMemo(() => {
    if (Platform.OS === 'web' && typeof window !== 'undefined') {
      return `${window.location.origin}/lead/${academyId ?? 1}`;
    }
    return academyId ? `/lead/${academyId}` : '';
  }, [academyId]);

  const load = useCallback(async () => {
    const path = filter ? `/api/v1/staff/leads?status=${filter}` : '/api/v1/staff/leads';
    const r = await apiGet<LeadsResponse>(path);
    if (r.ok) {
      setLeads(r.data.items || []);
      setCounts(r.data.counts || null);
    }
    setLoading(false);
    setRefreshing(false);
  }, [filter]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  async function patch(id: number, body: Partial<Lead>) {
    setBusyId(id);
    const r = await apiPatch<{ success: boolean; lead: Lead }>(`/api/v1/staff/leads/${id}`, body);
    setBusyId(null);
    if (r.ok && r.data.lead) {
      setLeads(prev => prev.map(l => (l.id === id ? r.data.lead : l)));
      // refresh counts
      load();
    } else {
      Alert.alert('Could not update', (r as any).error || 'Try again');
    }
  }

  function call(phone: string) {
    if (!phone) return;
    Linking.openURL(`tel:${phone.replace(/[^\d+]/g, '')}`);
  }
  function sms(phone: string) {
    if (!phone) return;
    Linking.openURL(`sms:${phone.replace(/[^\d+]/g, '')}`);
  }
  function email(addr: string) {
    if (!addr) return;
    Linking.openURL(`mailto:${addr}`);
  }

  function copyShareUrl() {
    if (!shareUrl) return;
    if (Platform.OS === 'web' && typeof navigator !== 'undefined' && (navigator as any).clipboard) {
      (navigator as any).clipboard.writeText(shareUrl);
      Alert.alert('Copied', shareUrl);
    } else {
      Alert.alert('Share link', shareUrl);
    }
  }

  if (!me || me.type !== 'staff') return null;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.tokens.bg.canvas }}>
      <Stack.Screen options={{ title: 'Leads' }} />
      <View style={{ flexDirection: 'row', alignItems: 'center', padding: spacing.lg, gap: spacing.md, borderBottomWidth: 1, borderBottomColor: t.tokens.border.subtle }}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <Text style={{ color: t.tokens.text.accent, fontSize: 16, fontWeight: '600' }}>‹ Back</Text>
        </Pressable>
        <Text style={{ flex: 1, fontSize: 20, fontWeight: '700', color: t.tokens.text.primary }}>Leads</Text>
        {counts && counts.new > 0 ? <Badge label={`${counts.new} new`} tone="warning" /> : null}
      </View>

      <ScrollView
        contentContainerStyle={{ padding: spacing.lg, paddingBottom: spacing.xxxl }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}
      >
        {/* Share-link card */}
        <Card variant="tinted" style={{ marginBottom: spacing.lg }}>
          <Text style={{ ...t.type.h3, color: t.tokens.text.primary, marginBottom: 4 }}>Share your lead form</Text>
          <Text style={{ ...t.type.body, color: t.tokens.text.secondary, marginBottom: spacing.sm }}>
            Send this link in DMs, post on Instagram, or paste in your bio. Anyone who fills it shows up here.
          </Text>
          <Text selectable style={{ fontFamily: 'Space Grotesk', fontSize: 13, color: t.tokens.text.accent, marginBottom: spacing.sm }}>{shareUrl}</Text>
          <Button label="Copy link" onPress={copyShareUrl} fullWidth={false} />
        </Card>

        {/* Filters */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8, paddingBottom: spacing.md }}>
          {STATUS_FILTERS.map(f => {
            const active = filter === f.key;
            const count = counts ? (f.key === '' ? counts.total : counts[f.key as keyof typeof counts]) : 0;
            return (
              <Pressable
                key={f.key || 'all'}
                onPress={() => setFilter(f.key)}
                style={{
                  paddingHorizontal: 14,
                  paddingVertical: 8,
                  borderRadius: radius.pill,
                  borderWidth: 1,
                  borderColor: active ? t.tokens.brand.accent : t.tokens.border.default,
                  backgroundColor: active ? t.tokens.bg.accentSoft : 'transparent',
                }}
              >
                <Text style={{ color: active ? t.tokens.text.accent : t.tokens.text.secondary, fontWeight: '600', fontSize: 13 }}>
                  {f.label} {count > 0 ? `(${count})` : ''}
                </Text>
              </Pressable>
            );
          })}
        </ScrollView>

        {loading ? (
          <Text style={{ color: t.tokens.text.muted, textAlign: 'center', padding: spacing.xl }}>Loading…</Text>
        ) : leads.length === 0 ? (
          <Card>
            <Text style={{ ...t.type.h3, color: t.tokens.text.primary, marginBottom: 4 }}>No leads yet</Text>
            <Text style={{ ...t.type.body, color: t.tokens.text.muted }}>
              Share your form link or paste the embed snippet on your gym site to start collecting leads.
            </Text>
          </Card>
        ) : (
          leads.map(lead => {
            const open = openId === lead.id;
            const fullName = `${lead.first_name} ${lead.last_name}`.trim() || '(no name)';
            const isBusy = busyId === lead.id;
            return (
              <Card
                key={lead.id}
                style={{ marginBottom: spacing.md }}
                onPress={() => setOpenId(open ? null : lead.id)}
              >
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <Text style={{ ...t.type.h3, color: t.tokens.text.primary, flex: 1 }}>{fullName}</Text>
                  <Badge label={lead.status} tone={statusTone(lead.status)} size="sm" />
                </View>
                <Text style={{ ...t.type.body, color: t.tokens.text.secondary, marginBottom: 4 }}>
                  {[lead.email, lead.phone].filter(Boolean).join(' · ') || '(no contact)'}
                </Text>
                <Text style={{ ...t.type.caption, color: t.tokens.text.muted }}>
                  {[lead.interested_in, lead.source].filter(Boolean).join(' · ')}{lead.interested_in || lead.source ? ' · ' : ''}{timeAgo(lead.created_at)}
                </Text>

                {open && (
                  <View style={{ marginTop: spacing.md, gap: 8 }}>
                    {lead.notes ? (
                      <View style={{ backgroundColor: t.tokens.bg.surfaceMuted, padding: 10, borderRadius: radius.md }}>
                        <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginBottom: 2 }}>NOTES</Text>
                        <Text style={{ ...t.type.body, color: t.tokens.text.secondary }}>{lead.notes}</Text>
                      </View>
                    ) : null}

                    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                      {lead.phone ? (
                        <>
                          <Button label="Call" onPress={() => call(lead.phone)} fullWidth={false} />
                          <Button label="SMS" variant="ghost" onPress={() => sms(lead.phone)} fullWidth={false} />
                        </>
                      ) : null}
                      {lead.email ? (
                        <Button label="Email" variant="ghost" onPress={() => email(lead.email)} fullWidth={false} />
                      ) : null}
                    </View>

                    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 }}>
                      {lead.status === 'new' && (
                        <Button label="Mark contacted" onPress={() => patch(lead.id, { status: 'contacted' })} fullWidth={false} />
                      )}
                      {lead.status !== 'converted' && (
                        <Button label="Mark converted" variant="ghost" onPress={() => patch(lead.id, { status: 'converted' })} fullWidth={false} />
                      )}
                      {lead.status !== 'lost' && (
                        <Button label="Mark lost" variant="ghost" onPress={() => patch(lead.id, { status: 'lost' })} fullWidth={false} />
                      )}
                      <Button label="Archive" variant="ghost" onPress={() => patch(lead.id, { archived: true })} fullWidth={false} />
                    </View>

                    {isBusy && <Text style={{ color: t.tokens.text.muted, fontSize: 12 }}>Saving…</Text>}
                  </View>
                )}
              </Card>
            );
          })
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
