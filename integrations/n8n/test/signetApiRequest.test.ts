import { signetApiRequest } from '../nodes/SignetProtocol/GenericFunctions';

// Minimal mock context replicating required n8n helper surface
function createContext(failures: number, statusCode = 503) {
  let calls = 0;
  const ctx: any = {
    getNode() { return { name: 'TestNode' }; },
    getCredentials() { return { apiKey: 'demo', signetUrl: 'http://localhost:9999' }; },
    helpers: {
      async httpRequestWithAuthentication(_name: string, opts: any) {
        calls += 1;
        if (calls <= failures) {
          const err: any = new Error('Temporary error');
            err.statusCode = statusCode;
            throw err;
        }
        return { data: { ok: true, method: opts.method, attempt: calls } };
      }
    }
  };
  return ctx;
}

describe('signetApiRequest retry logic', () => {
  it('succeeds without retries on first attempt', async () => {
    const ctx: any = createContext(0);
    const res = await signetApiRequest.call(ctx, 'GET', '/v1/test');
    expect(res.ok).toBe(true);
    expect(res.attempt).toBe(1);
  });

  it('retries on 503 and eventually succeeds', async () => {
    const ctx: any = createContext(2, 503);
    const start = Date.now();
    const res = await signetApiRequest.call(ctx, 'GET', '/v1/test', {}, {}, {}, { maxRetries: 5, baseDelayMs: 10, maxDelayMs: 50 });
    const elapsed = Date.now() - start;
    expect(res.ok).toBe(true);
    expect(res.attempt).toBe(3);
    expect(elapsed).toBeGreaterThanOrEqual(10); // some backoff occurred
  });

  it('does not retry unsafe POST when 503', async () => {
    const ctx: any = createContext(1, 503);
    await expect(signetApiRequest.call(ctx, 'POST', '/v1/test')).rejects.toThrow('Signet API request failed');
  });

  it('stops after max retries', async () => {
    const ctx: any = createContext(10, 503);
    await expect(signetApiRequest.call(ctx, 'GET', '/v1/test', {}, {}, {}, { maxRetries: 2, baseDelayMs: 5, maxDelayMs: 20 })).rejects.toThrow('Signet API request failed');
  });
});
