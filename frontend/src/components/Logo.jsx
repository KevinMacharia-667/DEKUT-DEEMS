import './Logo.css';

/**
 * DeKUT DEEMS logo.
 *
 * An original mark inspired by the university emblem's upward gold wings
 * and ribbon banner — redrawn as a simplified geometric icon that stays
 * legible from 16px (favicon) up to hero size.
 *
 * Props:
 *   size          icon height in px (default 40)
 *   onDark        use light wordmark colours (for the green navbar)
 *   showWordmark  render the "DeKUT DEEMS" wordmark beside the icon
 *   stacked       place the wordmark below the icon instead of beside it
 *   tagline       optional line of small text under the wordmark
 */
export default function Logo({
  size = 40,
  showWordmark = false,
  stacked = false,
  tagline = '',
  onDark = false,
  className = '',
}) {
  const gid = `logo${size}${stacked ? 's' : ''}`;

  return (
    <span className={`logo ${stacked ? 'logo-stacked' : ''} ${onDark ? 'logo-on-dark' : ''} ${className}`.trim()}>
      <svg
        className="logo-mark"
        width={size}
        height={size}
        viewBox="0 0 64 64"
        role="img"
        aria-label="DeKUT DEEMS"
      >
        <defs>
          <linearGradient id={`${gid}-g`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#3FC93D" />
            <stop offset="1" stopColor="#1B711B" />
          </linearGradient>
          <linearGradient id={`${gid}-y`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#FFD956" />
            <stop offset="1" stopColor="#E5A800" />
          </linearGradient>
        </defs>

        <rect width="64" height="64" rx="15" fill={`url(#${gid}-g)`} />

        {/* wings — two bars each side, sweeping up and outward */}
        <g stroke={`url(#${gid}-y)`} strokeWidth="6" strokeLinecap="round" fill="none">
          <path d="M27.5 40 L12 30" />
          <path d="M27.5 30 L12 20" />
          <path d="M36.5 40 L52 30" />
          <path d="M36.5 30 L52 20" />
        </g>

        {/* central spire */}
        <path
          d="M32 9 C36 17 37.5 26 37.5 44 L26.5 44 C26.5 26 28 17 32 9 Z"
          fill={`url(#${gid}-y)`}
        />

        {/* ribbon banner */}
        <rect x="12" y="49" width="40" height="6.5" rx="3.25" fill="#0D4F0D" />
        <rect x="16" y="51.2" width="32" height="2" rx="1" fill="#FFD956" opacity="0.9" />
      </svg>

      {showWordmark && (
        <span className="logo-text">
          <span className="logo-wordmark" style={{ fontSize: size * 0.46 }}>
            <span className="logo-word-dekut">DeKUT</span>
            <span className="logo-word-deems">DEEMS</span>
          </span>
          {tagline && <span className="logo-tagline">{tagline}</span>}
        </span>
      )}
    </span>
  );
}
