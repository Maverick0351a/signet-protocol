import { ICredentialType, INodeProperties } from 'n8n-workflow';

export class SignetProtocolApi implements ICredentialType {
	name = 'signetProtocolApi';
	displayName = 'Signet Protocol API';
	properties: INodeProperties[] = [
		{
			displayName: 'Signet URL',
			name: 'signetUrl',
			type: 'string',
			default: 'http://localhost:8088',
			description: 'Base URL of your Signet Protocol server (e.g. http://localhost:8088 for local dev or https://signet-protocol.fly.dev for hosted)',
		},
		{
			displayName: 'API Key',
			name: 'apiKey',
			type: 'string',
			typeOptions: { password: true },
			default: '',
			description: 'API key for authentication (X-SIGNET-API-Key header)',
		},
	];
}
