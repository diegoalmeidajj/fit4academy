import { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { Link } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useTheme, radius, spacing } from '@/lib/theme';
import { useAuth } from '@/store/auth';
import { Button } from '@/components/Button';
import { Icon } from '@/components/Icon';

type Mode = 'member' | 'staff';

const ERR_MAP: Record<string, string> = {
  invalid_credentials: 'Email or password is incorrect.',
  email_password_required: 'Please enter your email and password.',
  username_password_required: 'Please enter your username and password.',
  network_error: "Can't reach the server. Check your connection.",
  expired: 'Your session expired. Please sign in again.',
  invalid: 'Your session is invalid. Please sign in again.',
};

export default function LoginScreen() {
  const t = useTheme();
  const [mode, setMode] = useState<Mode>('member');
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [identifierFocused, setIdentifierFocused] = useState(false);
  const [passwordFocused, setPasswordFocused] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loginMember = useAuth(s => s.loginMember);
  const loginStaff = useAuth(s => s.loginStaff);

  async function handleSubmit() {
    if (submitting) return;
    setError(null);
    setSubmitting(true);
    const result =
      mode === 'member'
        ? await loginMember(identifier.trim(), password)
        : await loginStaff(identifier.trim(), password);
    setSubmitting(false);
    if (!result.ok) {
      setError(ERR_MAP[result.error || ''] || result.error || 'Sign in failed.');
    }
  }

  function inputBorder(focused: boolean) {
    if (error) return t.tokens.text.danger;
    return focused ? t.tokens.border.focus : t.tokens.border.default;
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.tokens.bg.canvas }}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={{
            flexGrow: 1,
            paddingHorizontal: spacing.xl,
            paddingTop: spacing.xxl,
            paddingBottom: spacing.xl,
            justifyContent: 'center',
          }}
          keyboardShouldPersistTaps="handled"
        >
          {/* Brand mark */}
          <View style={{ alignItems: 'center', marginBottom: spacing.xl }}>
            <View
              style={{
                width: 72, height: 72, borderRadius: 20,
                backgroundColor: t.tokens.brand.accent,
                alignItems: 'center', justifyContent: 'center',
                marginBottom: spacing.lg,
                shadowColor: t.tokens.brand.accent,
                shadowOpacity: t.mode === 'dark' ? 0.45 : 0.30,
                shadowRadius: 28,
                shadowOffset: { width: 0, height: 12 },
                elevation: 10,
              }}
            >
              <Text
                style={{
                  color: '#0f172a',
                  fontSize: 30,
                  fontWeight: '800',
                  letterSpacing: -1.5,
                }}
              >
                F4
              </Text>
            </View>
            <Text
              style={{
                fontSize: 30,
                fontWeight: '800',
                color: t.tokens.text.primary,
                letterSpacing: -1,
              }}
            >
              Fit4<Text style={{ color: t.tokens.brand.accent }}>Academy</Text>
            </Text>
            <Text
              style={{
                fontSize: 14,
                color: t.tokens.text.muted,
                marginTop: 6,
                textAlign: 'center',
              }}
            >
              {mode === 'member' ? 'Train. Track. Get better.' : 'Run your academy. Calmly.'}
            </Text>
          </View>

          {/* Mode tabs — segmented control */}
          <View
            style={{
              flexDirection: 'row',
              backgroundColor: t.tokens.bg.surfaceAlt,
              padding: 4,
              borderRadius: radius.md,
              marginBottom: spacing.xl,
            }}
          >
            {(['member', 'staff'] as Mode[]).map((m) => {
              const active = mode === m;
              return (
                <Pressable
                  key={m}
                  onPress={() => setMode(m)}
                  style={({ pressed }) => ({
                    flex: 1,
                    paddingVertical: 10,
                    borderRadius: radius.sm,
                    alignItems: 'center',
                    backgroundColor: active ? t.tokens.bg.surface : 'transparent',
                    shadowColor: '#000',
                    shadowOpacity: active ? (t.mode === 'dark' ? 0.3 : 0.06) : 0,
                    shadowRadius: 4,
                    shadowOffset: { width: 0, height: 1 },
                    elevation: active ? 1 : 0,
                    opacity: pressed ? 0.85 : 1,
                  })}
                >
                  <Text
                    style={{
                      fontSize: 13,
                      fontWeight: '700',
                      color: active ? t.tokens.text.primary : t.tokens.text.muted,
                      letterSpacing: 0.1,
                    }}
                  >
                    {m === 'member' ? 'Member' : 'Staff'}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          {/* Identifier */}
          <View style={{ marginBottom: spacing.md }}>
            <Text
              style={{
                fontSize: 12,
                fontWeight: '600',
                color: t.tokens.text.secondary,
                marginBottom: 8,
                letterSpacing: 0.1,
              }}
            >
              {mode === 'member' ? 'Email' : 'Username'}
            </Text>
            <TextInput
              style={{
                color: t.tokens.text.primary,
                fontSize: 15,
                paddingHorizontal: 16,
                paddingVertical: 14,
                borderWidth: 1.5,
                borderColor: inputBorder(identifierFocused),
                backgroundColor: t.tokens.bg.surface,
                borderRadius: radius.md,
              }}
              value={identifier}
              onChangeText={setIdentifier}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType={mode === 'member' ? 'email-address' : 'default'}
              placeholder={mode === 'member' ? 'you@email.com' : 'your.username'}
              placeholderTextColor={t.tokens.text.disabled}
              editable={!submitting}
              onFocus={() => setIdentifierFocused(true)}
              onBlur={() => setIdentifierFocused(false)}
            />
          </View>

          {/* Password */}
          <View style={{ marginBottom: spacing.lg }}>
            <Text
              style={{
                fontSize: 12,
                fontWeight: '600',
                color: t.tokens.text.secondary,
                marginBottom: 8,
                letterSpacing: 0.1,
              }}
            >
              Password
            </Text>
            <TextInput
              style={{
                color: t.tokens.text.primary,
                fontSize: 15,
                paddingHorizontal: 16,
                paddingVertical: 14,
                borderWidth: 1.5,
                borderColor: inputBorder(passwordFocused),
                backgroundColor: t.tokens.bg.surface,
                borderRadius: radius.md,
              }}
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoCapitalize="none"
              placeholder="••••••••"
              placeholderTextColor={t.tokens.text.disabled}
              editable={!submitting}
              onFocus={() => setPasswordFocused(true)}
              onBlur={() => setPasswordFocused(false)}
            />
          </View>

          {error && (
            <View
              style={{
                flexDirection: 'row',
                alignItems: 'center',
                gap: 8,
                paddingHorizontal: 12,
                paddingVertical: 10,
                borderRadius: radius.sm,
                backgroundColor: t.tokens.bg.dangerSoft,
                marginBottom: spacing.md,
              }}
            >
              <Icon name="close" size={14} color={t.tokens.text.danger} />
              <Text style={{ color: t.tokens.text.danger, fontSize: 13, flex: 1 }}>
                {error}
              </Text>
            </View>
          )}

          <Button label="Sign in" onPress={handleSubmit} loading={submitting} size="lg" />

          {mode === 'member' && (
            <Link href="/(auth)/signup" asChild>
              <Pressable
                style={({ pressed }) => ({
                  paddingVertical: spacing.md,
                  alignItems: 'center',
                  marginTop: spacing.md,
                  opacity: pressed ? 0.6 : 1,
                })}
              >
                <Text style={{ color: t.tokens.text.muted, fontSize: 13 }}>
                  First time?{' '}
                  <Text style={{ color: t.tokens.brand.accent, fontWeight: '700' }}>
                    Sign up with your gym PIN
                  </Text>
                </Text>
              </Pressable>
            </Link>
          )}

          {/* Trust line */}
          <View
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              marginTop: spacing.xl,
            }}
          >
            <Icon name="lock" size={12} color={t.tokens.text.muted} />
            <Text style={{ fontSize: 11, color: t.tokens.text.muted, letterSpacing: 0.3 }}>
              Secured by 256-bit encryption
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
