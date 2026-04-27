import { Image, View, Text, StyleSheet, ViewStyle } from 'react-native';
import { useTheme, radius } from '@/lib/theme';

type Props = {
  uri?: string | null;
  initials?: string;
  size?: number;
  style?: ViewStyle;
};

export function Avatar({ uri, initials, size = 48, style }: Props) {
  const t = useTheme();
  const dim: ViewStyle = {
    width: size,
    height: size,
    borderRadius: size / 4,
    backgroundColor: t.tokens.brand.accent,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  };

  if (uri) {
    return <Image source={{ uri }} style={[dim, style]} />;
  }

  return (
    <View style={[dim, style]}>
      <Text
        style={{
          color: t.tokens.text.onAccent,
          fontWeight: '800',
          fontSize: Math.max(12, size * 0.4),
          letterSpacing: -0.5,
        }}
      >
        {(initials || 'F4').toUpperCase()}
      </Text>
    </View>
  );
}
