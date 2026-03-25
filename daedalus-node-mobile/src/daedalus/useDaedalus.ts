import React from 'react';
import { DaedalusContext, type DaedalusContextExt } from './DaedalusProvider';

export function useDaedalus(): DaedalusContextExt {
  const ctx = React.useContext(DaedalusContext);
  if (!ctx) {
    throw new Error('useDaedalus must be used within a DaedalusProvider');
  }
  return ctx;
}
