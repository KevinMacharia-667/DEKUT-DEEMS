/**
 * Attendance wording for event cards, from the RSVP count and capacity.
 *
 *   no capacity          -> "7 going"
 *   capacity, room left  -> "42 / 60 going"
 *   under 10% left       -> "57 / 60 going", status "Few seats left"
 *   full                 -> "60 / 60 going", status "Full"
 */

const FEW_SEATS_SHARE = 0.1;

export function describeAttendance(rsvpCount, maxAttendees) {
  const going = Math.max(0, Number(rsvpCount) || 0);
  const capacity = Number(maxAttendees) || 0;

  if (capacity <= 0) {
    return { text: `${going} going`, status: null };
  }

  const text = `${going} / ${capacity} going`;
  const remaining = capacity - going;
  if (remaining <= 0) {
    return { text, status: 'full', statusText: 'Full' };
  }
  if (remaining < capacity * FEW_SEATS_SHARE) {
    return { text, status: 'few', statusText: 'Few seats left' };
  }
  return { text, status: null };
}
