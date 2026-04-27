import { useState } from 'react';
import {
  View, Text, TextInput, Pressable, KeyboardAvoidingView, Platform, ScrollView,
} from 'react-native';
import { Link } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useTheme, radius, spacing } from '@/lib/theme';
import { useAuth } from '@/store/auth';
import { Button } from '@/components/Button';

const ERR_MAP: Record<string, string> = {
  invalid_pin: "We couldn't find a member with that PIN. Ask your coach for the right one.",
  already_registered: 'This account is already set up. Sign in instead.',
  email_in_use: 'That email is already in use.',
  invalid_email: 'Please enter a valid email.',
  password_too_short: 'Password must be at least 8 characters.',
  pin_email_password_required: 'Please fill in all fields.',
};

export default function SignupScreen() {
  const t = useTheme();
  const [pin, setPin] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const signup = useAuth(s => s.signupMemberWithPin);

  async function handleSubmit() {
    if (submitting) return;
    setError(null);
    setSubmitting(true);
    const r = await signup(pin.trim(), email.trim(), password);
    setSubmitting(false);
    if (!r.ok) {
      setError(ERR_MAP[r.error || ''] || r.error || 'Sign up failed.');
    }
  }

  const fieldStyle = {
    color: t.tokens.text.primary, fontSize: 15,
    paddingHorizontal: 14, paddingVertical: 14,
    borderWidth: 1.5, borderColor: t.tokens.border.default,
    backgroundColor: t.tokens.bg.surface,
    borderRadius: radius.md,
  } as const;

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
          <Text style={{ fontSize: 28, fontWeight: '800', color: t.tokens.text.primary, letterSpacing: -0.5 }}>
            Set up your account
          </Text>
          <Text style={{ ...t.type.body, color: t.tokens.text.secondary, marginTop: 6, lineHeight: 22 }}>
            Enter the PIN your gym gave you (it's on your member QR card), then choose a login.
          </Text>

          <View style={{ marginTop: spacing.xl, marginBottom: spacing.lg }}>
            <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginBottom: 6 }}>MEMBER PIN</Text>
            <TextInput
              style={fieldStyle}
              value={pin}
              onChangeText={setPin}
              autoCapitalize="characters"
              placeholder="6-character code"
              placeholderTextColor={t.tokens.text.disabled}
              editable={!submitting}
            />
          </View>

          <View style={{ marginBottom: spacing.lg }}>
            <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginBottom: 6 }}>EMAIL</Text>
            <TextInput
              style={fieldStyle}
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
              placeholder="you@email.com"
              placeholderTextColor={t.tokens.text.disabled}
              editable={!submitting}
            />
          </View>

          <View style={{ marginBottom: spacing.lg }}>
            <Text style={{ ...t.type.caption, color: t.tokens.text.muted, marginBottom: 6 }}>CHOOSE A PASSWORD</Text>
            <TextInput
              style={fieldStyle}
              value={password}
              onChangeText={setPassword}
              secureTextEntry
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

          <Button label="Create account" onPress={handleSubmit} loading={submitting} size="lg" />

          <Link href="/(auth)/login" asChild>
            <Pressable style={{ paddingVertical: spacing.md, alignItems: 'center', marginTop: spacing.md }}>
              <Text style={{ color: t.tokens.text.muted, fontSize: 13 }}>
                Already have an account?{' '}
                <Text style={{ color: t.tokens.brand.accent, fontWeight: '700' }}>Sign in</Text>
              </Text>
            </Pressable>
          </Link>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
