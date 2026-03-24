export interface ApiRequest<T> {
    operatorId: string;
    payload: T;
}

export interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: string;
}
