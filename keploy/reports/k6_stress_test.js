import http from 'k6/http';
import { sleep } from 'k6';

export const options = {
  stages: [
    { duration: '10s', target: 10 },
    { duration: '20s', target: 50 },
    { duration: '20s', target: 100 },
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000'],
    http_req_failed: ['rate<0.10'],
  },
};

export default function () {
  const params = { headers: { Accept: 'application/json' }, timeout: '10s' };
  http.get("http://192.168.0.49:8080/api/v1/admin/analytics", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/audit", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/chemists", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/chemists", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/commissions/settings", params);
  sleep(0.3);
}
