/**
 * Screen — top-level wrapper that paints the canvas, sets safe areas,
 * and exposes a contentContainer scroll container with theme-aware padding.
 */
import { ReactNode } from 'react';
import { View, StyleSheet, ScrollView, RefreshControl, ScrollViewProps } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useTheme, spacing as s } from '@/lib/theme';

type Props = {
  children: ReactNode;
  scroll?: boolean;
  refreshing?: boolean;
  onRefresh?: () => void;
  padded?: boolean;
  edges?: ('top' | 'bottom' | 'left' | 'right')[];
  contentContainerStyle?: ScrollViewProps['contentContainerStyle'];
};

export function Screen({
  children,
  scroll = true,
  refreshing,
  onRefresh,
  padded = true,
  edges,
  contentContainerStyle,
}: Props) {
  const t = useTheme();
  const containerStyle = [
    styles.root,
    { backgroundColor: t.tokens.bg.canvas },
  ];
  const padStyle = padded ? { padding: s.xl, paddingBottom: s.xxxl } : null;

  if (!scroll) {
    return (
      <SafeAreaView style={containerStyle} edges={edges as any}>
        <View style={[{ flex: 1 }, padStyle]}>{children}</View>
      </SafeAreaView>
    );
  }
  return (
    <SafeAreaView style={containerStyle} edges={edges as any}>
      <ScrollView
        contentContainerStyle={[padStyle, contentContainerStyle]}
        refreshControl={
          onRefresh ? (
            <RefreshControl
              refreshing={!!refreshing}
              onRefresh={onRefresh}
              tintColor={t.tokens.brand.accent}
            />
          ) : undefined
        }
        showsVerticalScrollIndicator={false}
      >
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
});
