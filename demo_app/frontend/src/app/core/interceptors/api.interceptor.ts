import { HttpInterceptorFn } from '@angular/common/http';

// Requests go to /api on the same origin; `npm start` proxies them to the
// Conduit backend in demo_app/backend (see proxy.conf.json).
export const apiInterceptor: HttpInterceptorFn = (req, next) => {
  const apiReq = req.clone({ url: `/api${req.url}` });
  return next(apiReq);
};
