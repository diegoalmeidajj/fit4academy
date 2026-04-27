/**
 * Icon — SF Symbols-inspired SVG icon set, drawn at 24×24 with stroke 1.5.
 * Used everywhere instead of emoji for a clean, professional look.
 *
 * Add new glyphs by adding a key to PATHS below. Stick to outline style.
 */
import Svg, { Path, Circle } from 'react-native-svg';

export type IconName =
  | 'home'
  | 'calendar'
  | 'pin'
  | 'message'
  | 'person'
  | 'chevron-right'
  | 'chevron-left'
  | 'chevron-down'
  | 'chevron-up'
  | 'check'
  | 'check-circle'
  | 'close'
  | 'plus'
  | 'arrow-right'
  | 'arrow-left'
  | 'card'
  | 'trophy'
  | 'belt'
  | 'send'
  | 'lock'
  | 'face-id'
  | 'logout'
  | 'sun'
  | 'moon'
  | 'auto'
  | 'inbox'
  | 'bell'
  | 'search';

const PATHS: Record<IconName, React.ReactNode> = {
  home: (
    <Path d="M3 11l9-7 9 7M5 9.5V20a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V9.5"
      stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  calendar: (
    <>
      <Path d="M4 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7Z"
        stroke="currentColor" strokeWidth={1.5} fill="none" />
      <Path d="M8 3v4M16 3v4M4 10h16"
        stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" />
    </>
  ),
  pin: (
    <>
      <Path d="M12 21s7-5.5 7-11a7 7 0 1 0-14 0c0 5.5 7 11 7 11Z"
        stroke="currentColor" strokeWidth={1.5} fill="none" />
      <Circle cx={12} cy={10} r={2.5} stroke="currentColor" strokeWidth={1.5} fill="none" />
    </>
  ),
  message: (
    <Path d="M21 12c0 4.418-4.03 8-9 8a9.7 9.7 0 0 1-3.5-.65L4 21l1.5-3.5A7.5 7.5 0 0 1 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8Z"
      stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  person: (
    <>
      <Circle cx={12} cy={8} r={4} stroke="currentColor" strokeWidth={1.5} fill="none" />
      <Path d="M4 21c0-4 3.5-7 8-7s8 3 8 7"
        stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" fill="none" />
    </>
  ),
  'chevron-right': (
    <Path d="M9 6l6 6-6 6" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  'chevron-left': (
    <Path d="M15 6l-6 6 6 6" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  'chevron-down': (
    <Path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  'chevron-up': (
    <Path d="M6 15l6-6 6 6" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  check: (
    <Path d="M5 12l4.5 4.5L19 7" stroke="currentColor" strokeWidth={2}
      strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  'check-circle': (
    <>
      <Circle cx={12} cy={12} r={9} stroke="currentColor" strokeWidth={1.5} fill="none" />
      <Path d="M8 12.5l3 3 5-6" stroke="currentColor" strokeWidth={1.8}
        strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </>
  ),
  close: (
    <Path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  plus: (
    <Path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" fill="none" />
  ),
  'arrow-right': (
    <Path d="M5 12h14m0 0l-5-5m5 5l-5 5" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  'arrow-left': (
    <Path d="M19 12H5m0 0l5-5m-5 5l5 5" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  card: (
    <>
      <Path d="M2 7a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7Z"
        stroke="currentColor" strokeWidth={1.5} fill="none" />
      <Path d="M2 10h20" stroke="currentColor" strokeWidth={1.5} />
    </>
  ),
  trophy: (
    <Path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4ZM7 6H4v2a3 3 0 0 0 3 3M17 6h3v2a3 3 0 0 1-3 3"
      stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  belt: (
    <Path d="M3 12h18M3 12l3-4M3 12l3 4M21 12l-3-4M21 12l-3 4M9 8v8M15 8v8"
      stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" fill="none" />
  ),
  send: (
    <Path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7Z"
      stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  lock: (
    <>
      <Path d="M5 11h14v9a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-9Z"
        stroke="currentColor" strokeWidth={1.5} fill="none" />
      <Path d="M8 11V7a4 4 0 0 1 8 0v4"
        stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" fill="none" />
    </>
  ),
  'face-id': (
    <>
      <Path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2"
        stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" fill="none" />
      <Circle cx={9} cy={11} r={0.6} fill="currentColor" />
      <Circle cx={15} cy={11} r={0.6} fill="currentColor" />
      <Path d="M9 16c1 1 2 1.5 3 1.5s2-.5 3-1.5"
        stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" fill="none" />
    </>
  ),
  logout: (
    <Path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"
      stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  sun: (
    <>
      <Circle cx={12} cy={12} r={4} stroke="currentColor" strokeWidth={1.5} fill="none" />
      <Path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
        stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" />
    </>
  ),
  moon: (
    <Path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"
      stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  auto: (
    <>
      <Circle cx={12} cy={12} r={9} stroke="currentColor" strokeWidth={1.5} fill="none" />
      <Path d="M12 3v18M3 12a9 9 0 0 1 9-9 9 9 0 0 1 0 18"
        stroke="currentColor" strokeWidth={1.5} fill="none" />
    </>
  ),
  inbox: (
    <Path d="M3 13l3-9h12l3 9M3 13v6a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-6M3 13h5l1 3h6l1-3h5"
      stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  bell: (
    <Path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.94 1.94 0 0 0 3.4 0"
      stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  search: (
    <>
      <Circle cx={11} cy={11} r={7} stroke="currentColor" strokeWidth={1.5} fill="none" />
      <Path d="M21 21l-4.5-4.5" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" />
    </>
  ),
};

type Props = {
  name: IconName;
  size?: number;
  color?: string;
};

export function Icon({ name, size = 24, color = 'currentColor' }: Props) {
  const node = PATHS[name];
  if (!node) return null;
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" color={color} fill="none">
      {node}
    </Svg>
  );
}
