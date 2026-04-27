/**
 * Geofence helpers — distance calculation + permission flow.
 *
 * The actual background geofence (`Location.startGeofencingAsync`) is wired in
 * the screen that uses it, because it requires a registered TaskManager task.
 * Here we just handle: requesting permissions, getting current position, and
 * computing distance from a point.
 */
import * as Location from 'expo-location';

export type Coords = { lat: number; lng: number };

const EARTH_RADIUS_M = 6_371_000;

/** Haversine distance, in meters. */
export function distanceMeters(a: Coords, b: Coords): number {
  const toRad = (x: number) => (x * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(h));
}

export async function requestForegroundPermission(): Promise<{
  granted: boolean;
  canAskAgain: boolean;
}> {
  const r = await Location.requestForegroundPermissionsAsync();
  return { granted: r.granted, canAskAgain: r.canAskAgain };
}

export async function getCurrentPosition(): Promise<Coords | null> {
  try {
    const r = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });
    return { lat: r.coords.latitude, lng: r.coords.longitude };
  } catch {
    return null;
  }
}
