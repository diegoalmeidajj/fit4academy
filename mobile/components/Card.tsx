import { ReactNode } from 'react';
import { View, ViewStyle, StyleSheet, Pressable } from 'react-native';

import { useTheme, radius, spacing } from '@/lib/theme';

type Props = {
  children: ReactNode;
  style?: ViewStyle | ViewStyle[];
  variant?: 'default' | 'elevated' | 'tinted' | 'outlined';
  tintColor?: string;
  onPress?: () => void;
  padded?: boolean;
};

export function Card({
  children,
  style,
  variant = 'default',
  tintColor,
  onPress,
  padded = true,
}: Props) {
  const t = useTheme();

  const base: ViewStyle = {
    borderRadius: radius.lg,
    padding: padded ? spacing.lg : 0,
    backgroundColor: t.tokens.bg.surface,
    borderWidth: 1,
    borderColor: t.tokens.border.subtle,
  };

  if (variant === 'elevated') {
    base.backgroundColor = t.tokens.bg.elevated;
    base.borderColor = t.tokens.border.subtle;
    Object.assign(base, {
      shadowColor: t.tokens.shadow.elevatedColor,
      shadowOpacity: t.tokens.shadow.elevatedOpacity,
      shadowRadius: 24,
      shadowOffset: { width: 0, height: 8 },
      elevation: 6,
    });
  } else if (variant === 'tinted') {
    base.backgroundColor = tintColor || t.tokens.bg.accentSoft;
    base.borderColor = tintColor ? 'transparent' : t.tokens.border.accent;
  } else if (variant === 'outlined') {
    base.backgroundColor = 'transparent';
    base.borderColor = t.tokens.border.default;
  }

  if (onPress) {
    return (
      <Pressable
        onPress={onPress}
        style={({ pressed }) => [base, style, pressed && styles.pressed]}
      >
        {children}
      </Pressable>
    );
  }
  return <View style={[base, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  pressed: { opacity: 0.85, transform: [{ scale: 0.99 }] },
});
