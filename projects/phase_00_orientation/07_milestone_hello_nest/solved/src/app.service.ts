import { Injectable } from '@nestjs/common';

// The controller only delegates; the text lives in the service so that unit
// tests can check it without starting an HTTP server (see topic 1.4).
@Injectable()
export class AppService {
  getHello(): string {
    return 'Hello, Nest 12!';
  }
}
