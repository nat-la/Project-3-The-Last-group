/**
 * Leaflet marker asset fix (Vite / modern bundlers)
 *
 * Problem:
 * - Leaflet’s default marker icons rely on hardcoded relative paths.
 * - In bundlers like Vite, these assets are not automatically resolved,
 *   causing missing marker icons (broken image / invisible markers).
 *
 * Solution:
 * - Manually import the marker image assets so the bundler includes them
 * - Override Leaflet’s default icon URL resolution
 */

import L from "leaflet";

// Import marker image assets so Vite resolves them correctly
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";

/**
 * Remove Leaflet’s internal method that tries to resolve icon URLs dynamically.
 * This forces it to use the URLs we explicitly provide below.
 *
 * NOTE:
 * - _getIconUrl is a private/internal method, so this is a workaround,
 *   but it’s a widely accepted fix in Leaflet + bundler setups.
 */
delete L.Icon.Default.prototype._getIconUrl;

/**
 * Override default marker icon configuration globally.
 * All <Marker /> components will now use these resolved asset URLs.
 */
L.Icon.Default.mergeOptions({
  iconRetinaUrl,
  iconUrl,
  shadowUrl,
});