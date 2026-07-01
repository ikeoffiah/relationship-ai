import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 50,
  duration: '2m',
  thresholds: {
    http_req_duration: ['p(99)<200'], // Safety pre-screen p99 < 200ms
  },
};

export default function () {
  const baseUrl = __ENV.BASE_URL || 'http://localhost:8000';
  
  const res = http.post(
    `${baseUrl}/api/v1/safety/pre-screen`,
    JSON.stringify({ content: 'I feel a bit sad today.' }),
    {
      headers: { 'Content-Type': 'application/json' }
    }
  );
  
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(1);
}
