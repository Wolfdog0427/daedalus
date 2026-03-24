export interface DaedalusFunction {
    id: string;
    name: string;
    description: string;
    parameters: Record<string, any>;
    returns: Record<string, any>;
}

export interface FunctionRegistry {
    functions: DaedalusFunction[];
}
