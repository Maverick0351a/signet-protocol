import {
	IExecuteFunctions,
	IHookFunctions,
	ILoadOptionsFunctions,
	IWebhookFunctions,
	IHttpRequestOptions,
	NodeApiError,
} from 'n8n-workflow';

/**
 * Make an API request to Signet Protocol
 */
export async function signetApiRequest(
	this: IHookFunctions | IExecuteFunctions | ILoadOptionsFunctions | IWebhookFunctions,
	method: string,
	resource: string,
	body: any = {},
	qs: any = {},
	headers: any = {},
	option: any = {},
): Promise<any> {
	const credentials = await this.getCredentials('signetProtocolApi');

	const baseUrl = (credentials.signetUrl as string).replace(/\/$/, '');

	const options: IHttpRequestOptions = {
		method,
		headers: {
			'Content-Type': 'application/json',
			'X-SIGNET-API-Key': credentials.apiKey as string,
			'User-Agent': 'n8n-signet-protocol/1.0.0',
			...headers,
		},
		body,
		qs,
		url: `${baseUrl}${resource}`,
		json: true,
	};

	if (Object.keys(body).length === 0) {
		delete options.body;
	}

	if (Object.keys(qs).length === 0) {
		delete options.qs;
	}

	try {
		if (option.returnFullResponse) {
			return await this.helpers.httpRequestWithAuthentication.call(this, 'signetProtocolApi', options);
		}
		return await this.helpers.httpRequestWithAuthentication.call(this, 'signetProtocolApi', options);
	} catch (error) {
		throw new NodeApiError(this.getNode(), error);
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
