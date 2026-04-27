import { ActivityIndicator, Pressable, StyleSheet, Text, ViewStyle } from 'react-native';
import { useTheme, radius, spacing, type as typeS } from '@/lib/theme';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';

type Props = {
  label: string;
  onPress?: () => void;
  variant?: Variant;
  loading?: boolean;
  disabled?: boolean;
  fullWidth?: boolean;
  size?: 'sm' | 'md' | 'lg';
  icon?: string;
  style?: ViewStyle;
};

export function Button({
  label,
  onPress,
  variant = 'primary',
  loading,
  disabled,
  fullWidth = true,
  size = 'md',
  icon,
  style,
}: Props) {
  const t = useTheme();
  const sizing =
    size === 'sm'
      ? { paddingVertical: 10, paddingHorizontal: 14, fontSize: 13 }
      : size === 'lg'
      ? { paddingVertical: 16, paddingHorizontal: 24, fontSize: 16 }
      : { paddingVertical: 14, paddingHorizontal: 20, fontSize: 15 };

  let bg = t.tokens.brand.accent;
  let fg = t.tokens.text.onAccent;
  let borderColor = 'transparent';
  let borderWidth = 0;
  let shadow = {
    shadowColor: t.tokens.brand.accent,
    shadowOpacity: 0.25,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  };

  if (variant === 'secondary') {
    bg = t.tokens.bg.accentSoft;
    fg = t.tokens.text.accent;
    borderColor = t.tokens.border.accent;
    borderWidth = 1.5;
    shadow = { ...shadow, shadowOpacity: 0 };
  } else if (variant === 'ghost') {
    bg = 'transparent';
    fg = t.tokens.text.secondary;
    borderColor = t.tokens.border.default;
    borderWidth = 1;
    shadow = { ...shadow, shadowOpacity: 0 };
  } else if (variant === 'danger') {
    bg = t.tokens.text.danger;
    fg = '#ffffff';
    shadow = { ...shadow, shadowColor: t.tokens.text.danger, shadowOpacity: 0.2 };
  }

  const isDisabled = disabled || loading;

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      style={({ pressed }) => [
        {
          backgroundColor: bg,
          paddingVertical: sizing.paddingVertical,
          paddingHorizontal: sizing.paddingHorizontal,
          borderRadius: radius.md,
          borderWidth,
          borderColor,
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 8,
          alignSelf: fullWidth ? 'stretch' : 'flex-start',
          opacity: isDisabled ? 0.5 : pressed ? 0.92 : 1,
          transform: [{ scale: pressed ? 0.99 : 1 }],
        },
        shadow,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={fg} size="small" />
      ) : (
        <>
          {icon && <Text style={{ fontSize: sizing.fontSize + 2 }}>{icon}</Text>}
          <Text
            style={{
              color: fg,
              fontSize: sizing.fontSize,
              fontWeight: '700',
              letterSpacing: 0.2,
            }}
          >
            {label}
          </Text>
        </>
      )}
    </Pressable>
  );
}
