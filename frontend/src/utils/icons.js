/**
 * Icon lookups shared across screens (lucide-react). Emoji render differently
 * on Android, iOS and Windows, so the UI uses one icon set everywhere.
 */
import {
  BookOpen,
  Briefcase,
  CalendarDays,
  Compass,
  Drama,
  Flame,
  GraduationCap,
  Laptop,
  PartyPopper,
  Pin,
  Sparkles,
  Star,
  Trophy,
  Wrench,
  Zap,
} from 'lucide-react';

const CATEGORY_ICONS = {
  Academic: BookOpen,
  Social: PartyPopper,
  Sports: Trophy,
  Workshop: Wrench,
  Cultural: Drama,
  Tech: Laptop,
  Career: Briefcase,
};

/** Icon component for an event category (calendar icon when unknown). */
export function categoryIcon(category) {
  return CATEGORY_ICONS[category] || CalendarDays;
}

/** Cover background for an event without an image, from the --cat-* tokens in index.css. */
export function categoryCover(category) {
  const key = CATEGORY_ICONS[category] ? category.toLowerCase() : 'default';
  return `linear-gradient(135deg, var(--cat-${key}-deep) 0%, var(--cat-${key}) 100%)`;
}

// Leading emoji / symbols the backend puts on badge strings ("🔥 Trending on Campus")
// (pictographs, optionally joined by ZWJ / followed by a variation selector)
const LEADING_SYMBOLS = /^(?:\p{Extended_Pictographic}|‍|️|\s)+/u;

const BADGE_ICONS = [
  [/trending/i, Flame],
  [/soon|today/i, Zap],
  [/faculty|school|department/i, GraduationCap],
  [/for you/i, Sparkles],
  [/explore/i, Compass],
  [/recommended|content match/i, Star],
];

/** Split a badge like "🔥 Trending on Campus" into { Icon, label: "Trending on Campus" }. */
export function splitBadge(text) {
  const label = String(text || '').replace(LEADING_SYMBOLS, '').trim();
  const match = BADGE_ICONS.find(([pattern]) => pattern.test(label));
  return { Icon: match ? match[1] : Pin, label };
}
