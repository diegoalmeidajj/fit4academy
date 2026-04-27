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

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.tokens.bg.canvas }}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={{ flexGrow: 1, padding: spacing.xl, paddingTop: 60, paddingBottom: spacing.xl }}
          keyboardShouldPersistTaps="handled"
        >
          {/* Brand */}
          <View style={{ alignItems: 'center', marginBottom: spacing.xxl }}>
            <View style={{
              width: 80, height: 80, borderRadius: radius.lg,
              backgroundColor: t.tokens.brand.accent,
              alignItems: 'center', justifyContent: 'center',
              marginBottom: spacing.md,
              shadowColor: t.tokens.brand.accent, shadowOpacity: 0.4,
              shadowRadius: 24, shadowOffset: { width: 0, height: 8 }, elevation: 8,
            }}>
              <Text style={{ color: '#fff', fontSize: 32, fontWeight: '800', letterSpacing: -1 }}>F4</Text>
            </View>
            <Text style={{ fontSize: 32, fontWeight: '800', color: t.tokens.text.primary, letterSpacing: -1 }}>
              Fit4<Text style={{ color: t.tokens.brand.accent }}>Academy</Text>
            </Text>
            <Text style={{ ...t.type.body, color: t.tokens.text.muted, marginTop: 8 }}>
              {mode === 'member' ? 'Welcome back, athlete.' : 'Welcome back, coach.'}
            </Text>
          </View>

          {/* Mode tabs */}
          <View style={{
            flexDirection: 'row',
            backgroundColor: t.tokens.bg.surfaceMuted,
            padding: 4,
            borderRadius: radius.md,
            marginBottom: spacing.xl,
            borderWidth: 1, borderColor: t.tokens.border.subtle,
          }}>
            {(['member', 'staff'] as Mode[]).map((m) => {
              const active = mode === m;
              return (
                <Pressable
                  key={m}
                  onPress={() => setMode(m)}
                  style={{
                    flex: 1, paddingVertical: 11, borderRadius: radius.sm, alignItems: 'center',
                    backgroundColor: active ? t.tokens.brand.accent : 'transparent',
                  }}
                >
                  <Text style={{
                    fontSize: 13, fontWeight: '700',
                    color: active ? t.tokens.text.onAccent : t.tokens.text.muted,
                  }}>
                    {m === 'member' ? "I'm a member" : "I'm staff"}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          {/* Identifier */}
          <View style={{ marginBottom: spacing.lg }}>
            <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginBottom: 6 }}>
              {mode === 'member' ? 'EMAIL' : 'USERNAME'}
            </Text>
            <TextInput
              style={{
                color: t.tokens.text.primary, fontSize: 15,
                paddingHorizontal: 14, paddingVertical: 14,
                borderWidth: 1.5, borderColor: t.tokens.border.default,
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
            />
          </View>

          {/* Password */}
          <View style={{ marginBottom: spacing.lg }}>
            <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginBottom: 6 }}>PASSWORD</Text>
            <TextInput
              style={{
                color: t.tokens.text.primary, fontSize: 15,
                paddingHorizontal: 14, paddingVertical: 14,
                borderWidth: 1.5, borderColor: t.tokens.border.default,
                backgroundColor: t.tokens.bg.surface,
                borderRadius: radius.md,
              }}
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoCapitalize="none"
              placeholder="At least 8 characters"
              placeholderTextColor={t.tokens.text.disabled}
              editable={!submitting}
            />
          </View>

          {error && (
            <Text style={{ color: t.tokens.text.danger, fontSize: 13, marginBottom: spacing.md, textAlign: 'center' }}>
              {error}
            </Text>
          )}

          <Button label="Sign in" onPress={handleSubmit} loading={submitting} size="lg" />

          {mode === 'member' && (
            <Link href="/(auth)/signup" asChild>
              <Pressable style={{ paddingVertical: spacing.md, alignItems: 'center', marginTop: spacing.md }}>
                <Text style={{ color: t.tokens.text.muted, fontSize: 13 }}>
                  First time?{' '}
                  <Text style={{ color: t.tokens.brand.accent, fontWeight: '700' }}>
                    Sign up with your gym PIN →
                  </Text>
                </Text>
              </Pressable>
            </Link>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
