/**
 * OMEN SDK Error Classes
 */

/**
 * Base error class for OMEN SDK
 */
export class OmenError extends Error {
  public statusCode?: number;
  public errorCode?: string;
  public details?: Record<string, unknown>;

  constructor(
    message: string,
    options?: {
      statusCode?: number;
      errorCode?: string;
      details?: Record<string, unknown>;
    }
  ) {
    super(message);
    this.name = 'OmenError';
    this.statusCode = options?.statusCode;
    this.errorCode = options?.errorCode;
    this.details = options?.details;
  }
}

/**
 * Raised when authentication fails
 */
export class AuthenticationError extends OmenError {
  constructor(message = 'Authentication failed', details?: Record<string, unknown>) {
    super(message, { statusCode: 401, errorCode: 'AUTHENTICATION_FAILED', details });
    this.name = 'AuthenticationError';
  }
}

/**
 * Raised when authorization fails
 */
export class AuthorizationError extends OmenError {
  public requiredScopes?: string[];

  constructor(
    message = 'Access denied',
    options?: { requiredScopes?: string[]; details?: Record<string, unknown> }
  ) {
    super(message, { statusCode: 403, errorCode: 'AUTHORIZATION_FAILED', details: options?.details });
    this.name = 'AuthorizationError';
    this.requiredScopes = options?.requiredScopes;
  }
}

/**
 * Raised when rate limit is exceeded
 */
export class RateLimitError extends OmenError {
  public retryAfter?: number;
  public limit?: number;
  public remaining?: number;

  constructor(
    message = 'Rate limit exceeded',
    options?: {
      retryAfter?: number;
      limit?: number;
      remaining?: number;
      details?: Record<string, unknown>;
    }
  ) {
    super(message, { statusCode: 429, errorCode: 'RATE_LIMIT_EXCEEDED', details: options?.details });
    this.name = 'RateLimitError';
    this.retryAfter = options?.retryAfter;
    this.limit = options?.limit;
    this.remaining = options?.remaining;
  }
}

/**
 * Raised when a resource is not found
 */
export class NotFoundError extends OmenError {
  public resourceType?: string;
  public resourceId?: string;

  constructor(
    message = 'Resource not found',
    options?: {
      resourceType?: string;
      resourceId?: string;
      details?: Record<string, unknown>;
    }
  ) {
    super(message, { statusCode: 404, errorCode: 'NOT_FOUND', details: options?.details });
    this.name = 'NotFoundError';
    this.resourceType = options?.resourceType;
    this.resourceId = options?.resourceId;
  }
}

/**
 * Raised when request validation fails
 */
export class ValidationError extends OmenError {
  public errors?: Array<{ field: string; message: string }>;

  constructor(
    message = 'Validation failed',
    options?: {
      errors?: Array<{ field: string; message: string }>;
      details?: Record<string, unknown>;
    }
  ) {
    super(message, { statusCode: 422, errorCode: 'VALIDATION_FAILED', details: options?.details });
    this.name = 'ValidationError';
    this.errors = options?.errors;
  }
}

/**
 * Raised when server encounters an error
 */
export class ServerError extends OmenError {
  constructor(message = 'Internal server error', statusCode = 500) {
    super(message, { statusCode, errorCode: 'SERVER_ERROR' });
    this.name = 'ServerError';
  }
}

/**
 * Handle HTTP response and throw appropriate error
 */
export function handleResponseError(response: Response, data?: unknown): never {
  const errorData = data as Record<string, unknown> | undefined;
  const message = (errorData?.message as string) || (errorData?.detail as string) || response.statusText;
  const errorCode = errorData?.error as string | undefined;
  const details = errorData?.details as Record<string, unknown> | undefined;

  switch (response.status) {
    case 401:
      throw new AuthenticationError(message, details);
    case 403:
      throw new AuthorizationError(message, { details });
    case 404:
      throw new NotFoundError(message, { details });
    case 422:
      throw new ValidationError(message, { details });
    case 429: {
      const retryAfter = response.headers.get('Retry-After');
      throw new RateLimitError(message, {
        retryAfter: retryAfter ? parseInt(retryAfter, 10) : undefined,
        details,
      });
    }
    default:
      if (response.status >= 500) {
        throw new ServerError(message, response.status);
      }
      throw new OmenError(message, { statusCode: response.status, errorCode, details });
  }
}
