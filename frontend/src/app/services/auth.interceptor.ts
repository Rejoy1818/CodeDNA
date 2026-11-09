import {
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
} from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

/**
 * AuthInterceptor attaches the stored API key to outgoing requests.
 *
 * The API key is expected to be stored in localStorage under the key
 * `codedna_api_key` after the user logs in / provides it. Requests to
 * the health endpoint are left unauthenticated.
 */
@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const apiKey = typeof localStorage !== 'undefined' ? localStorage.getItem('codedna_api_key') : null;

    if (apiKey) {
      req = req.clone({
        setHeaders: { 'X-API-Key': apiKey },
      });
    }

    return next.handle(req);
  }
}
