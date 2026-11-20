import { Module } from '@nestjs/common';
import { AuthModule } from './auth/auth.module';
import { UserModule } from './user/user.module';
import { UseduleModule } from './bookmark/usedule/usedule.module';

@Module({
  imports: [AuthModule, UserModule, UseduleModule],
  controllers: [],
  providers: [],
})
export class AppModule {}
