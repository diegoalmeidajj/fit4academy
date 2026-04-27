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

type ClassItem = {
  class_id: number;
  name: string;
  instructor: string;
  class_type: string;
  start_time: string;
  end_time: string;
  duration: number | null;
};
type Day = {
  date: string;
  day_label: string;
  is_today: boolean;
  classes: ClassItem[];
};

export default function ScheduleScreen() {
  const router = useRouter();
  const [days, setDays] = useState<Day[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const r = await apiGet<{ days: Day[] }>('/api/v1/me/schedule');
    if (r.ok) setDays(r.data.days || []);
    setLoading(false);
    setRefreshing(false);
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));
  useEffect(() => { load(); }, [load]);

  return (
    <SafeAreaView style={styles.root}>
      <View style={styles.header}>
        <Text style={styles.title}>Schedule</Text>
        <Pressable onPress={() => router.push('/(member)/events')} style={styles.eventBtn}>
          <Text style={styles.eventBtnLabel}>🏆 Events</Text>
        </Pressable>
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
        {loading && days.length === 0 ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.green} size="large" />
          </View>
        ) : (
          days.map((d) => (
            <View key={d.date} style={styles.dayBlock}>
              <View style={styles.dayHeader}>
                <Text style={[styles.dayLabel, d.is_today && { color: colors.green }]}>
                  {d.is_today ? 'TODAY' : d.day_label.toUpperCase()}
                </Text>
                <Text style={styles.dayDate}>{d.date}</Text>
              </View>

              {d.classes.length === 0 ? (
                <View style={styles.emptyDay}>
                  <Text style={styles.emptyDayText}>No classes scheduled</Text>
                </View>
              ) : (
                d.classes.map((c, idx) => (
                  <View key={`${c.class_id}-${idx}`} style={styles.classCard}>
                    <View style={styles.timeBox}>
                      <Text style={styles.timeText}>{c.start_time}</Text>
                      <Text style={styles.timeSub}>{c.end_time}</Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.className}>{c.name}</Text>
                      {!!c.instructor && (
                        <Text style={styles.classMeta}>👤 {c.instructor}</Text>
                      )}
                      {!!c.class_type && (
                        <Text style={styles.classMeta}>🥋 {c.class_type}</Text>
                      )}
                    </View>
                  </View>
                ))
              )}
            </View>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bgDeep },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing.xl,
    paddingBottom: spacing.md,
  },
  title: { ...typeS.h1, color: '#fff' },
  eventBtn: {
    backgroundColor: 'rgba(0,220,130,0.1)',
    borderWidth: 1,
    borderColor: colors.green,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: radius.md,
  },
  eventBtnLabel: { color: colors.green, fontWeight: '700', fontSize: 13 },
  scroll: { paddingHorizontal: spacing.xl, paddingBottom: spacing.xxl },
  center: { paddingVertical: 80, alignItems: 'center' },

  dayBlock: { marginBottom: spacing.lg },
  dayHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderDark,
    marginBottom: spacing.sm,
  },
  dayLabel: { ...typeS.caption, color: colors.textMuted, letterSpacing: 0.6 },
  dayDate: { ...typeS.caption, color: colors.textMuted },

  classCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderRadius: radius.md,
    marginBottom: 8,
    gap: spacing.md,
  },
  timeBox: {
    backgroundColor: 'rgba(0,220,130,0.1)',
    borderRadius: radius.sm,
    paddingHorizontal: 10,
    paddingVertical: 6,
    minWidth: 64,
    alignItems: 'center',
  },
  timeText: { color: colors.green, fontWeight: '700', fontSize: 14 },
  timeSub: { color: colors.textMuted, fontSize: 10 },
  className: { color: '#fff', fontWeight: '700', fontSize: 15 },
  classMeta: { color: colors.textMuted, fontSize: 12, marginTop: 2 },

  emptyDay: {
    paddingVertical: spacing.md,
    alignItems: 'center',
  },
  emptyDayText: { color: colors.textMuted, fontSize: 13, fontStyle: 'italic' },
});
