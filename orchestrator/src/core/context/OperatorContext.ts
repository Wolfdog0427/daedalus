export interface OperatorSnapshot {
  id: string | null;
  label: string | null;
  roles: string[];
}

export class OperatorContext {
  private current: OperatorSnapshot = {
    id: null,
    label: null,
    roles: [],
  };

  public setOperator(id: string, label?: string, roles: string[] = []) {
    this.current = {
      id,
      label: label ?? id,
      roles,
    };
  }

  public clearOperator() {
    this.current = {
      id: null,
      label: null,
      roles: [],
    };
  }

  public getCurrentOperator(): OperatorSnapshot {
    return this.current;
  }

  public getSnapshot(): OperatorSnapshot {
    return this.current;
  }
}

export function createOperatorContext(): OperatorContext {
  return new OperatorContext();
}
