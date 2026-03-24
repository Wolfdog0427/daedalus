export interface Operator {
    id: string;
    name: string;
    role: "primary" | "secondary" | "guest";
    createdAt: number;
    updatedAt: number;
}

export interface OperatorRegistry {
    operators: Operator[];
    primaryOperatorId: string;
}
