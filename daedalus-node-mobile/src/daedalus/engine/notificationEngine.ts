import { NotificationPayload } from '../types';

export function routeNotification(payload: NotificationPayload) {
  const prefix = `[Daedalus:${payload.level.toUpperCase()}]`;
  // eslint-disable-next-line no-console
  console.log(prefix, payload.message, payload.meta ?? {});
}
