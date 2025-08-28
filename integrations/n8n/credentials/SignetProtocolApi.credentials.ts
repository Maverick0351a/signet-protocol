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
			description: 'Base URL of your Signet Protocol server',
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
