/**
 * Wrappers around expo-local-authentication. Returns simple booleans so callers
 * don't have to remember the multi-step API.
 */
import * as LocalAuthentication from 'expo-local-authentication';
import { Platform } from 'react-native';

export type BiometricKind = 'face' | 'fingerprint' | 'iris' | 'none';

export async function biometricCapability(): Promise<{
  available: boolean;
  enrolled: boolean;
  kind: BiometricKind;
  label: string;
}> {
  if (Platform.OS === 'web') {
    return { available: false, enrolled: false, kind: 'none', label: 'Not supported on web' };
  }
  const hasHw = await LocalAuthentication.hasHardwareAsync();
  const enrolled = await LocalAuthentication.isEnrolledAsync();
  const types = await LocalAuthentication.supportedAuthenticationTypesAsync();
  let kind: BiometricKind = 'none';
  let label = 'Biometric';
  if (types.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION)) {
    kind = 'face';
    label = Platform.OS === 'ios' ? 'Face ID' : 'Face unlock';
  } else if (types.includes(LocalAuthentication.AuthenticationType.FINGERPRINT)) {
    kind = 'fingerprint';
    label = Platform.OS === 'ios' ? 'Touch ID' : 'Fingerprint';
  } else if (types.includes(LocalAuthentication.AuthenticationType.IRIS)) {
    kind = 'iris';
    label = 'Iris scan';
  }
  return { available: hasHw && enrolled, enrolled, kind, label };
}

export async function authenticate(reason: string): Promise<{ ok: boolean; error?: string }> {
  if (Platform.OS === 'web') return { ok: false, error: 'unsupported_platform' };
  try {
    const result = await LocalAuthentication.authenticateAsync({
      promptMessage: reason,
      cancelLabel: 'Cancel',
      disableDeviceFallback: false,
    });
    if (result.success) return { ok: true };
    return { ok: false, error: result.error || 'cancelled' };
  } catch (e: any) {
    return { ok: false, error: e?.message || 'unknown' };
  }
}
