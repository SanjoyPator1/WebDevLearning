import { Injectable } from '@nestjs/common';

@Injectable({})
export class AuthService {
  signup() {
    return { msg: 'I am signup from service' };
  }

  signin() {
    return { msg: 'I am signin from service' };
  }
}
