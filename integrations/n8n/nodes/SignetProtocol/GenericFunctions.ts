import {
	IExecuteFunctions,
	IHookFunctions,
	ILoadOptionsFunctions,
	IWebhookFunctions,
	IHttpRequestOptions,
	IHttpRequestMethods,
	NodeApiError,
} from 'n8n-workflow';

interface SignetCredentials {
	apiKey: string;
	signetUrl: string;
}

/**
 * Make an API request to Signet Protocol
 */
export async function signetApiRequest(
	this: IHookFunctions | IExecuteFunctions | ILoadOptionsFunctions | IWebhookFunctions,
	method: string,
	resource: string,
	body: any = {},
	qs: any = {},
	headers: Record<string, any> = {},
	option: Record<string, any> = {},
): Promise<any> {
	const credentials = await this.getCredentials('signetProtocolApi') as unknown as SignetCredentials;
	if (!credentials) {
		throw new NodeApiError(this.getNode(), { message: 'Missing Signet Protocol credentials' });
	}

	// Normalize base URL (strip trailing slash) & resource (ensure leading slash)
	const baseUrl = credentials.signetUrl.replace(/\/$/, '');
	const normalizedResource = resource.startsWith('/') ? resource : `/${resource}`;

	const httpMethod = method.toUpperCase() as IHttpRequestMethods;
	const options: IHttpRequestOptions = {
		method: httpMethod,
		headers: {
			'Content-Type': 'application/json',
			'X-SIGNET-API-Key': credentials.apiKey,
			'User-Agent': 'n8n-signet-protocol/1.0.0',
			...headers,
		},
		body,
		qs,
		url: `${baseUrl}${normalizedResource}`,
		json: true,
		timeout: 30_000,
	};

	// Merge any caller-supplied override options (e.g., timeout, proxy, gzip, etc.)
	if (option && Object.keys(option).length) {
		Object.assign(options, option);
		// Allow header overrides inside option.headers
		if (option.headers) {
			options.headers = { ...options.headers, ...option.headers };
		}
	}

	// Remove body for GET / HEAD automatically
	if (['GET', 'HEAD'].includes(options.method || '') || !body || Object.keys(body).length === 0) {
		delete options.body;
	}
	if (!qs || Object.keys(qs).length === 0) {
		delete options.qs;
	}

	// Retry / backoff settings (can be overridden via option)
	const maxRetries: number = option.maxRetries ?? 3;
	const baseDelayMs: number = option.baseDelayMs ?? 500;
	const maxDelayMs: number = option.maxDelayMs ?? 4000;
	const retryOnStatuses: number[] = option.retryOnStatuses ?? [429, 502, 503, 504];
	const safeRetryMethods = new Set(['GET', 'HEAD', 'OPTIONS']);

	let attempt = 0;
	while (true) {
		try {
			const response = await this.helpers.httpRequestWithAuthentication.call(this, 'signetProtocolApi', options);
			return option.returnFullResponse ? response : (response?.data ?? response);
		} catch (error: any) {
			const status = error?.httpCode || error?.statusCode || error?.cause?.statusCode;
			const isRetryable = status && retryOnStatuses.includes(Number(status));
			const allowRetry = attempt < maxRetries && isRetryable && safeRetryMethods.has(options.method as string);
			if (!allowRetry) {
				throw new NodeApiError(this.getNode(), error as any, { message: 'Signet API request failed', description: `attempt=${attempt+1}` });
			}
			// Exponential backoff with jitter
			const delay = Math.min(maxDelayMs, baseDelayMs * Math.pow(2, attempt));
			const jitter = Math.random() * (delay * 0.2);
			await new Promise(res => setTimeout(res, delay + jitter));
			attempt += 1;
		}
	}
}

/**
 * Make a paginated API request
 */
export async function signetApiRequestAllItems(
	this: IExecuteFunctions | ILoadOptionsFunctions,
	propertyName: string,
	method: string,
	endpoint: string,
	body: any = {},
	query: any = {},
): Promise<any> {
	const returnData: any[] = [];

	let responseData;
	query.limit = 100;
	query.offset = 0;

	do {
		responseData = await signetApiRequest.call(this, method, endpoint, body, query);
		query.offset += query.limit;
		returnData.push.apply(returnData, responseData[propertyName]);
	} while (responseData[propertyName] && responseData[propertyName].length !== 0);

	return returnData;
}

/**
 * Validate JSON payload
 */
export function validateJsonPayload(payload: any): boolean {
	try {
		if (typeof payload === 'string') {
			JSON.parse(payload);
		} else if (typeof payload === 'object') {
			JSON.stringify(payload);
		} else {
			return false;
		}
		return true;
	} catch (error) {
		return false;
	}
}

/**
 * Generate trace ID for n8n workflows
 */
export function generateTraceId(workflowId?: string, executionId?: string): string {
	const timestamp = Date.now();
	const random = Math.random().toString(36).substr(2, 9);
	
	if (workflowId && executionId) {
		return `n8n-${workflowId}-${executionId}-${timestamp}`;
	}
	
	return `n8n-${timestamp}-${random}`;
}

/**
 * Format Signet response for n8n
 */
export function formatSignetResponse(response: any, operation: string, additionalData: any = {}): any {
	return {
		operation,
		timestamp: new Date().toISOString(),
		...response,
		...additionalData,
	};
}

/**
 * Check if data looks like an invoice
 */
export function isInvoiceLikeData(data: any): boolean {
	if (typeof data !== 'object' || data === null) {
		return false;
	}

	const invoiceFields = ['amount', 'currency', 'invoice_id', 'customer', 'description', 'total', 'price'];
	return invoiceFields.some(field => field in data);
}

/**
 * Convert data to Signet payload format
 */
export function convertToSignetPayload(data: any): any {
	if (isInvoiceLikeData(data)) {
		return {
			tool_calls: [{
				type: 'function',
				function: {
					name: 'create_invoice',
					arguments: JSON.stringify(data)
				}
			}]
		};
	}

	// For other data types, wrap in a generic tool call
	return {
		tool_calls: [{
			type: 'function',
			function: {
				name: 'process_data',
				arguments: JSON.stringify(data)
			}
		}]
	};
}
