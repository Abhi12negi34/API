import http from 'k6/http';
import { sleep } from 'k6';

export const options = {
  stages: [
    { duration: '5s',  target: 5   },
    { duration: '5s',  target: 200 },
    { duration: '5s',  target: 5   },
    { duration: '10s', target: 5   },
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'],
    http_req_failed: ['rate<0.15'],
  },
};

export default function () {
  const params = { headers: { Accept: 'application/json' }, timeout: '10s' };
  http.get("http://192.168.0.49:8080/api/v1/admin/analytics", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/audit", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/chemists", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/chemists", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/commissions/settings", params);
  sleep(0.1);
}
