import { siWhatsapp } from 'simple-icons';

/** The WhatsApp brand glyph (Simple Icons, CC0). Colour comes from CSS (--whatsapp). */
export default function WhatsAppIcon({ size = 16, className = '' }) {
  return (
    <svg
      className={`whatsapp-icon ${className}`.trim()}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      focusable="false"
    >
      <path d={siWhatsapp.path} />
    </svg>
  );
}
