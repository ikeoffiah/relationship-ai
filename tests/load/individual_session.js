import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 20,       // 20 virtual users
  duration: '5m', // 5-minute sustained test
  thresholds: {
    http_req_duration: ['p(99)<3000'], // LLM response p99 < 3s
    http_req_failed: ['rate<0.01'],    // error rate < 1%
  },
};

export default function () {
  const baseUrl = __ENV.BASE_URL || 'http://localhost:8000';
  
  // 1. Auth
  const authRes = http.post(`${baseUrl}/api/v1/auth/token`, JSON.stringify({
    username: 'user@example.com',
    password: 'password123'
  }), {
    headers: { 'Content-Type': 'application/json' }
  });
  const token = authRes.json('access_token');
  
  // 2. Start session
  const sessionRes = http.post(`${baseUrl}/api/v1/sessions`,
    JSON.stringify({ session_type: 'individual' }),
    {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      }
    }
  );
  const sessionId = sessionRes.json('session_id');
  
  // 3. Send message
  const msgRes = http.post(
    `${baseUrl}/api/v1/sessions/${sessionId}/messages`,
    JSON.stringify({ content: 'I feel like my partner never listens to me.' }),
    {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      }
    }
  );
  check(msgRes, { 'response received': (r) => r.status === 200 });
  
  sleep(10); // Think time between messages
}
