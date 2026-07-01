import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 20,
  duration: '3m',
  thresholds: {
    http_req_duration: ['p(95)<100'],
  },
};

export default function () {
  const baseUrl = __ENV.BASE_URL || 'http://localhost:8000';
  
  const res = http.post(
    `${baseUrl}/api/v1/memory/retrieve`,
    JSON.stringify({ query: 'how to resolve time conflicts' }),
    {
      headers: { 'Content-Type': 'application/json' }
    }
  );
  
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(2);
}
