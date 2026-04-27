import { useCallback, useEffect, useRef, useState } from 'react';
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
import { useFocusEffect } from 'expo-router';

import { colors, radius, spacing, type as typeS } from '@/lib/theme';
import { apiGet, apiPost } from '@/lib/api';
import { useAuth } from '@/store/auth';

type Msg = {
  id: number;
  sender_type: 'member' | 'staff';
  body: string;
  created_at: string;
  read_at: string | null;
};

export default function ChatScreen() {
  const me = useAuth(s => s.me);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const scrollRef = useRef<ScrollView>(null);

  const load = useCallback(async () => {
    const r = await apiGet<{ items: Msg[] }>('/api/v1/me/chat/messages');
    if (r.ok) setMessages(r.data.items || []);
    setLoading(false);
  }, []);

  useFocusEffect(useCallback(() => {
    load();
    // poll every 5s while screen is focused
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]));

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    // scroll to bottom on new messages
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 50);
  }, [messages.length]);

  async function send() {
    if (sending) return;
    const body = draft.trim();
    if (!body) return;
    setSending(true);
    setDraft('');
    const r = await apiPost('/api/v1/me/chat/messages', { body });
    setSending(false);
    if (r.ok) {
      load();
    } else {
      setDraft(body); // restore
    }
  }

  return (
    <SafeAreaView style={styles.root} edges={['top']}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={80}
      >
        <View style={styles.header}>
          <Text style={styles.title}>Message your coach</Text>
          <Text style={styles.sub}>{me?.type === 'member' ? me.academy?.name : ''}</Text>
        </View>

        {loading && messages.length === 0 ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.green} size="large" />
          </View>
        ) : (
          <ScrollView
            ref={scrollRef}
            style={{ flex: 1 }}
            contentContainerStyle={styles.list}
            onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: false })}
          >
            {messages.length === 0 ? (
              <View style={styles.empty}>
                <Text style={styles.emptyIcon}>💬</Text>
                <Text style={styles.emptyTitle}>Start the conversation</Text>
                <Text style={styles.emptyText}>
                  Send your coach a message — questions about training, schedule,
                  or anything else.
                </Text>
              </View>
            ) : (
              messages.map((m) => {
                const mine = m.sender_type === 'member';
                return (
                  <View
                    key={m.id}
                    style={[styles.bubble, mine ? styles.bubbleMine : styles.bubbleTheirs]}
                  >
                    <Text style={mine ? styles.bubbleTextMine : styles.bubbleTextTheirs}>
                      {m.body}
                    </Text>
                    <Text style={styles.bubbleTime}>
                      {m.created_at.slice(11, 16)}
                    </Text>
                  </View>
                );
              })
            )}
          </ScrollView>
        )}

        <View style={styles.inputRow}>
          <TextInput
            style={styles.input}
            value={draft}
            onChangeText={setDraft}
            placeholder="Type a message…"
            placeholderTextColor={colors.textMuted}
            multiline
            maxLength={4000}
          />
          <Pressable
            disabled={sending || !draft.trim()}
            onPress={send}
            style={[styles.sendBtn, (!draft.trim() || sending) && styles.sendBtnDisabled]}
          >
            {sending ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.sendLabel}>Send</Text>
            )}
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bgDeep },
  header: {
    padding: spacing.xl,
    paddingBottom: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderDark,
  },
  title: { ...typeS.h2, color: '#fff' },
  sub: { ...typeS.caption, color: colors.textMuted, marginTop: 2 },

  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  list: { padding: spacing.md, gap: 8 },

  empty: { paddingVertical: 60, alignItems: 'center' },
  emptyIcon: { fontSize: 56, marginBottom: spacing.md },
  emptyTitle: { ...typeS.h3, color: '#fff', marginBottom: 4 },
  emptyText: {
    color: colors.textMuted,
    textAlign: 'center',
    fontSize: 14,
    paddingHorizontal: spacing.xl,
    lineHeight: 20,
  },

  bubble: {
    maxWidth: '78%',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 16,
    marginBottom: 4,
  },
  bubbleMine: {
    alignSelf: 'flex-end',
    backgroundColor: colors.green,
    borderBottomRightRadius: 4,
  },
  bubbleTheirs: {
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderBottomLeftRadius: 4,
  },
  bubbleTextMine: { color: '#fff', fontSize: 14, lineHeight: 19 },
  bubbleTextTheirs: { color: '#fff', fontSize: 14, lineHeight: 19 },
  bubbleTime: { color: 'rgba(255,255,255,0.6)', fontSize: 10, marginTop: 4, alignSelf: 'flex-end' },

  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.borderDark,
    gap: 8,
  },
  input: {
    flex: 1,
    color: '#fff',
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: 1,
    borderColor: colors.borderDark,
    borderRadius: radius.md,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    maxHeight: 120,
  },
  sendBtn: {
    backgroundColor: colors.green,
    borderRadius: radius.md,
    paddingHorizontal: 16,
    paddingVertical: 12,
    minWidth: 64,
    alignItems: 'center',
  },
  sendBtnDisabled: { opacity: 0.4 },
  sendLabel: { color: '#fff', fontWeight: '700', fontSize: 14 },
});
