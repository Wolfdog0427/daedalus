import React from 'react';
import { DaedalusContext } from './DaedalusProvider';

export function useDaedalus() {
  const ctx = React.useContext(DaedalusContext);
  if (!ctx) {
    throw new Error('useDaedalus must be used within a DaedalusProvider');
  }
  return ctx;
}
