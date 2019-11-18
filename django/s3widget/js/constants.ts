export const DEFAULT_BASE_URL = '/api/joist';
import Cookies from 'js-cookie';

export function fetchOptions(): RequestInit {
  return {
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': Cookies.get('csrftoken')!
    },
  }
}
