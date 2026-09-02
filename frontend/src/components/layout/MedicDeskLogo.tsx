/** MedicDesk.ai mark — a four-petal pinwheel, recreated as inline SVG (not
 * a raster asset) so it scales crisply and recolors with the brand theme.
 * Modeled on the provided brand artwork's central glyph, in the amber/dark
 * palette used throughout the app instead of that artwork's cyan. */
export function MedicDeskLogo({ size = 32 }: { size?: number }) {
  const petal = "M50,50 C34,44 28,20 50,8 C72,20 66,44 50,50 Z";
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden="true">
      <defs>
        <radialGradient id="medicdesk-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#f6cf7a" />
          <stop offset="55%" stopColor="#e0a83a" />
          <stop offset="100%" stopColor="#a9741c" />
        </radialGradient>
      </defs>
      <circle cx="50" cy="50" r="48" fill="#0a0f0c" stroke="#26392e" strokeWidth="2" />
      <g fill="url(#medicdesk-glow)">
        <path d={petal} />
        <path d={petal} transform="rotate(90 50 50)" />
        <path d={petal} transform="rotate(180 50 50)" />
        <path d={petal} transform="rotate(270 50 50)" />
      </g>
      <circle cx="50" cy="50" r="6" fill="#0a0f0c" />
    </svg>
  );
}
