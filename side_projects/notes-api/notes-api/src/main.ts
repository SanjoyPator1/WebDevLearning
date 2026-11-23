import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { ValidationPipe } from '@nestjs/common';
import { HttpExceptionFilter } from './common/filters/http-exception.filter';
import { AllExceptionFilter } from './common/filters/all-exceptions.filter';
import { TimingInterceptor } from './common/interceptors/timing.interceptor';
import { ResponseWrapInterceptor } from './common/interceptors/response-wrap.interceptor';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // NOT NEEDED NOW
  // app.useGlobalGuards(new ApiKeyGuard());

  app.useGlobalInterceptors(
    new TimingInterceptor(),
    new ResponseWrapInterceptor(),
  );
  app.useGlobalPipes(new ValidationPipe({ whitelist: true }));

  app.useGlobalFilters(new AllExceptionFilter(), new HttpExceptionFilter());

  await app.listen(process.env.PORT ?? 3000);
}
void bootstrap();
