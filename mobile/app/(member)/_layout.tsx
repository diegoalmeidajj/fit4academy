import { Tabs } from 'expo-router';
import { View } from 'react-native';

import { useTheme } from '@/lib/theme';
import { Icon, IconName } from '@/components/Icon';

function TabIcon({ name, focused, color }: { name: IconName; focused: boolean; color: string }) {
  return (
    <View style={{ alignItems: 'center', justifyContent: 'center', height: 28 }}>
      <Icon name={name} size={focused ? 26 : 24} color={color} />
    </View>
  );
}

export default function MemberLayout() {
  const t = useTheme();
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: t.tokens.bg.surface,
          borderTopColor: t.tokens.border.subtle,
          borderTopWidth: 0.5,
          height: 78,
          paddingBottom: 14,
          paddingTop: 10,
          shadowColor: '#000',
          shadowOpacity: t.mode === 'dark' ? 0.4 : 0.04,
          shadowRadius: 12,
          shadowOffset: { width: 0, height: -4 },
          elevation: 8,
        },
        tabBarActiveTintColor: t.tokens.brand.accent,
        tabBarInactiveTintColor: t.tokens.text.muted,
        tabBarLabelStyle: {
          fontSize: 10.5,
          fontWeight: '600',
          letterSpacing: 0.2,
          marginTop: 2,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Home',
          tabBarIcon: ({ focused, color }) => <TabIcon name="home" focused={focused} color={color} />,
        }}
      />
      <Tabs.Screen
        name="schedule"
        options={{
          title: 'Schedule',
          tabBarIcon: ({ focused, color }) => <TabIcon name="calendar" focused={focused} color={color} />,
        }}
      />
      <Tabs.Screen
        name="checkin"
        options={{
          title: 'Check in',
          tabBarIcon: ({ focused, color }) => <TabIcon name="pin" focused={focused} color={color} />,
        }}
      />
      <Tabs.Screen
        name="chat"
        options={{
          title: 'Chat',
          tabBarIcon: ({ focused, color }) => <TabIcon name="message" focused={focused} color={color} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'More',
          tabBarIcon: ({ focused, color }) => <TabIcon name="person" focused={focused} color={color} />,
        }}
      />
      {/* Hidden screens reachable via stack push */}
      <Tabs.Screen name="payments" options={{ href: null }} />
      <Tabs.Screen name="events" options={{ href: null }} />
      <Tabs.Screen name="promotion" options={{ href: null }} />
    </Tabs>
  );
}
