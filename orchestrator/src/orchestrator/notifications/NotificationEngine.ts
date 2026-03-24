import type { Logger } from '../../infrastructure/logging.js';
import type { OrchestratorEventBus } from '../../shared/types.js';
import { randomUUID } from 'node:crypto';

export interface DaedalusNotification {
  id: string;
  type: string;
  payload: any;
  timestamp: string;
}

export interface NotificationEngineDeps {
  logger: Logger;
  eventBus: OrchestratorEventBus;
}

const MAX_NOTIFICATIONS = 100;

export class NotificationEngine {
  private readonly logger: Logger;
  private readonly eventBus: OrchestratorEventBus;
  private notifications: DaedalusNotification[] = [];

  constructor(deps: NotificationEngineDeps) {
    this.logger = deps.logger;
    this.eventBus = deps.eventBus;
  }

  public send(type: string, payload: any): DaedalusNotification {
    const notification: DaedalusNotification = {
      id: randomUUID(),
      type,
      payload,
      timestamp: new Date().toISOString(),
    };

    this.notifications.push(notification);
    if (this.notifications.length > MAX_NOTIFICATIONS) {
      this.notifications.shift();
    }

    this.logger.info('[notifications] sent', { type, id: notification.id });
    this.eventBus.publish({
      type: 'notification.sent',
      payload: notification,
    });

    return notification;
  }

  public onEvent(event: any): void {
    if (event.type === 'posture.changed') {
      this.send('posture_shift', {
        mode: event.payload?.mode,
        reason: event.payload?.reason,
      });
    }

    if (event.type === 'risk.detected') {
      this.send('risk_alert', { detail: event.payload });
    }
  }

  public list(): DaedalusNotification[] {
    return [...this.notifications];
  }

  public recent(count: number): DaedalusNotification[] {
    return this.notifications.slice(-count);
  }
}

export function createNotificationEngine(
  deps: NotificationEngineDeps,
): NotificationEngine {
  return new NotificationEngine(deps);
}
