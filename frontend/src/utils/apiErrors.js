/**
 * Human-readable messages for failed API calls, so screens never show raw
 * browser errors such as "Failed to fetch" or "Unexpected end of JSON input".
 */

export const SERVER_UNREACHABLE_MESSAGE =
  "We can't reach the Tukio server right now. Please try again in a moment.";
export const OFFLINE_MESSAGE = "You're offline. Reconnect to load the latest campus events.";

/**
 * Message for an HTTP error response.
 * @param {number} status  HTTP status code
 * @param {unknown} data   Parsed JSON body, or null when the body was not JSON
 */
export function describeApiError(status, data) {
  const detail = data && typeof data === 'object' ? data.detail : undefined;

  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }
  // FastAPI validation errors: detail is a list of { loc, msg, type }
  if (Array.isArray(detail) && detail.length > 0 && detail[0]?.msg) {
    const field = Array.isArray(detail[0].loc) ? detail[0].loc[detail[0].loc.length - 1] : null;
    return field ? `${field}: ${detail[0].msg}` : detail[0].msg;
  }
  if (status >= 500 || data === null) {
    return SERVER_UNREACHABLE_MESSAGE;
  }
  return 'Something went wrong. Please try again.';
}

/** Message for a request that never got a response (network down, server stopped). */
export function describeNetworkFailure(isOnline) {
  return isOnline === false ? OFFLINE_MESSAGE : SERVER_UNREACHABLE_MESSAGE;
}
