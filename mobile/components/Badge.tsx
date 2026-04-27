import { View, Text, ViewStyle } from 'react-native';
import { useTheme, radius } from '@/lib/theme';

type Tone = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'accent';

type Props = {
  label: string;
  tone?: Tone;
  size?: 'sm' | 'md';
  pill?: boolean;
  style?: ViewStyle;
};

export function Badge({ label, tone = 'neutral', size = 'md', pill = true, style }: Props) {
  const t = useTheme();
  const map: Record<Tone, { bg: string; fg: string; border: string }> = {
    success: { bg: t.tokens.bg.accentSoft, fg: t.tokens.text.success, border: t.tokens.text.success },
    warning: { bg: t.tokens.bg.warningSoft, fg: t.tokens.text.warning, border: t.tokens.text.warning },
    danger: { bg: t.tokens.bg.dangerSoft, fg: t.tokens.text.danger, border: t.tokens.text.danger },
    info: { bg: t.tokens.bg.infoSoft, fg: t.tokens.brand.accentCyan, border: t.tokens.brand.accentCyan },
    neutral: { bg: t.tokens.bg.surfaceMuted, fg: t.tokens.text.secondary, border: t.tokens.border.default },
    accent: { bg: t.tokens.bg.accentSoft, fg: t.tokens.text.accent, border: t.tokens.brand.accent },
  };
  const m = map[tone];
  return (
    <View
      style={[
        {
          paddingHorizontal: size === 'sm' ? 8 : 10,
          paddingVertical: size === 'sm' ? 3 : 5,
          backgroundColor: m.bg,
          borderRadius: pill ? radius.pill : radius.sm,
          borderWidth: 1,
          borderColor: m.border,
          alignSelf: 'flex-start',
        },
        style,
      ]}
    >
      <Text
        style={{
          color: m.fg,
          fontSize: size === 'sm' ? 10 : 11,
          fontWeight: '700',
          letterSpacing: 0.5,
        }}
      >
        {label.toUpperCase()}
      </Text>
    </View>
  );
}
