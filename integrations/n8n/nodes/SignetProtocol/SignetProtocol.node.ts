import {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
	NodeOperationError,
} from 'n8n-workflow';

import { signetApiRequest } from './GenericFunctions';

export class SignetProtocol implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Signet Protocol',
		name: 'signetProtocol',
		icon: 'file:signet.svg',
		group: ['transform'],
		version: 1,
		subtitle: '={{$parameter["operation"]}}',
		description: 'Interact with Signet Protocol for verified AI-to-AI communications',
		defaults: {
			name: 'Signet Protocol',
		},
		inputs: ['main'],
		outputs: ['main'],
		credentials: [
			{
				name: 'signetProtocolApi',
				required: true,
			},
		],
		properties: [
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				options: [
					{
						name: 'Create Exchange',
						value: 'createExchange',
						description: 'Create a verified exchange through Signet Protocol',
						action: 'Create a verified exchange',
					},
					{
						name: 'Get Receipt Chain',
						value: 'getReceiptChain',
						description: 'Retrieve a receipt chain by trace ID',
						action: 'Get a receipt chain',
					},
					{
						name: 'Export Chain Bundle',
						value: 'exportChain',
						description: 'Export a signed receipt chain bundle',
						action: 'Export a chain bundle',
					},
					{
						name: 'Get Billing Dashboard',
						value: 'getBillingDashboard',
						description: 'Get billing dashboard information',
						action: 'Get billing dashboard',
					},
				],
				default: 'createExchange',
			},

			// Create Exchange fields
			{
				displayName: 'Payload Type',
				name: 'payloadType',
				type: 'string',
				default: 'openai.tooluse.invoice.v1',
				description: 'Source payload type',
				displayOptions: {
					show: {
						operation: ['createExchange'],
					},
				},
			},
			{
				displayName: 'Target Type',
				name: 'targetType',
				type: 'string',
				default: 'invoice.iso20022.v1',
				description: 'Target payload type',
				displayOptions: {
					show: {
						operation: ['createExchange'],
					},
				},
			},
			{
				displayName: 'Payload Data',
				name: 'payloadData',
				type: 'json',
				default: '{}',
				description: 'The payload data to exchange',
				displayOptions: {
					show: {
						operation: ['createExchange'],
					},
				},
			},
			{
				displayName: 'Forward URL',
				name: 'forwardUrl',
				type: 'string',
				default: '',
				description: 'Optional URL to forward normalized data',
				displayOptions: {
					show: {
						operation: ['createExchange'],
					},
				},
			},
			{
				displayName: 'Trace ID',
				name: 'traceId',
				type: 'string',
				default: '',
				description: 'Optional trace ID for chaining (auto-generated if not provided)',
				displayOptions: {
					show: {
						operation: ['createExchange'],
					},
				},
			},

			// Get Receipt Chain / Export Chain fields
			{
				displayName: 'Trace ID',
				name: 'traceId',
				type: 'string',
				default: '',
				required: true,
				description: 'Trace ID to retrieve',
				displayOptions: {
					show: {
						operation: ['getReceiptChain', 'exportChain'],
					},
				},
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];
		const operation = this.getNodeParameter('operation', 0);

		for (let i = 0; i < items.length; i++) {
			try {
				let responseData;

				if (operation === 'createExchange') {
					// Create Exchange operation
					const payloadType = this.getNodeParameter('payloadType', i) as string;
					const targetType = this.getNodeParameter('targetType', i) as string;
					const payloadData = this.getNodeParameter('payloadData', i) as object;
					const forwardUrl = this.getNodeParameter('forwardUrl', i) as string;
					let traceId = this.getNodeParameter('traceId', i) as string;

					// Generate trace ID if not provided
					if (!traceId) {
						traceId = `n8n-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
					}

					// Generate idempotency key
					const idempotencyKey = `n8n-${traceId}-${Date.now()}`;

					// Prepare exchange data
					const exchangeData: any = {
						payload_type: payloadType,
						target_type: targetType,
						payload: payloadData,
						trace_id: traceId,
					};

					if (forwardUrl) {
						exchangeData.forward_url = forwardUrl;
					}

					// Make the request
					responseData = await signetApiRequest.call(
						this,
						'POST',
						'/v1/exchange',
						exchangeData,
						{},
						{ 'X-SIGNET-Idempotency-Key': idempotencyKey }
					);

					// Format response
					responseData = {
						...responseData,
						operation: 'createExchange',
						trace_id: traceId,
					};

				} else if (operation === 'getReceiptChain') {
					// Get Receipt Chain operation
					const traceId = this.getNodeParameter('traceId', i) as string;

					responseData = await signetApiRequest.call(
						this,
						'GET',
						`/v1/receipts/chain/${traceId}`,
					);

					responseData = {
						operation: 'getReceiptChain',
						trace_id: traceId,
						chain: responseData,
						chain_length: Array.isArray(responseData) ? responseData.length : 0,
					};

				} else if (operation === 'exportChain') {
					// Export Chain operation
					const traceId = this.getNodeParameter('traceId', i) as string;

					const response = await signetApiRequest.call(
						this,
						'GET',
						`/v1/receipts/export/${traceId}`,
						{},
						{},
						{},
						{ returnFullResponse: true }
					);

					responseData = {
						operation: 'exportChain',
						trace_id: traceId,
						...response.body,
						signature_headers: {
							bundle_cid: response.headers['x-odin-response-cid'],
							signature: response.headers['x-odin-signature'],
							kid: response.headers['x-odin-kid'],
						},
					};

				} else if (operation === 'getBillingDashboard') {
					// Get Billing Dashboard operation
					responseData = await signetApiRequest.call(
						this,
						'GET',
						'/v1/billing/dashboard',
					);

					responseData = {
						operation: 'getBillingDashboard',
						...responseData,
					};

				} else {
					throw new NodeOperationError(
						this.getNode(),
						`Unknown operation: ${operation}`,
						{ itemIndex: i }
					);
				}

				returnData.push({
					json: responseData,
					pairedItem: {
						item: i,
					},
				});

			} catch (error) {
				if (this.continueOnFail()) {
					returnData.push({
						json: {
							error: error.message,
							operation,
						},
						pairedItem: {
							item: i,
						},
					});
					continue;
				}
				throw error;
			}
		}

		return [returnData];
	}
}
