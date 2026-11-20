import { AuthService } from './auth.service';
import { Controller, Post } from '@nestjs/common';

@Controller('auth')
export class AuthController {
  constructor(private authService: AuthService) {}

  //route : auth/signup
  @Post('signup')
  signup() {
    return this.authService.signup();
  }

  //route : auth/signin
  @Post('signin')
  signin() {
    return this.authService.signin();
  }
}
