import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
  vus: 10,
  duration: '15s',
  thresholds: {
    http_req_duration: ['p(95)<2000'],
    http_req_failed: ['rate<0.05'],
  },
};

export default function () {
  const params = { headers: { 'Accept': 'application/json' }, timeout: '8s' };
  http.get("http://192.168.0.49:8080/api/v1/admin/analytics", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/audit", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/chemists", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/chemists", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/commissions/settings", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/distributors", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/distributors", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/orders", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/products", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/qr-analytics", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/tiers", params);
  http.get("http://192.168.0.49:8080/api/v1/admin/users", params);
  http.get("http://192.168.0.49:8080/api/v1/catalog/categories", params);
  http.get("http://192.168.0.49:8080/api/v1/catalog/products", params);
  http.get("http://192.168.0.49:8080/api/v1/commissions/pending", params);
  http.get("http://192.168.0.49:8080/api/v1/notifications", params);
  http.get("http://192.168.0.49:8080/api/v1/reports/admin/stats", params);
  http.get("http://192.168.0.49:8080/src/components/auth-shell.tsx", params);
  http.get("http://192.168.0.49:8080/src/lib/auth.ts", params);
  http.get("http://192.168.0.49:8080/src/routes/admin.analytics.tsx", params);
  sleep(0.5);
}
