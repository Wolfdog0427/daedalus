import type { Logger } from './logging.js';
import type {
  OrchestratorEventBus,
  OrchestratorEventBusSubscription,
} from '../shared/types.js';

export function createEventBus(logger: Logger): OrchestratorEventBus {
  const subscribers = new Set<(event: any) => void>();

  function publish(event: any) {
    logger.debug('[event-bus] publish', { type: event.type });
    for (const sub of subscribers) {
      sub(event);
    }
  }

  function subscribe(
    handler: (event: any) => void,
  ): OrchestratorEventBusSubscription {
    subscribers.add(handler);
    return {
      unsubscribe() {
        subscribers.delete(handler);
      },
    };
  }

  return { publish, subscribe };
}
