import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { ValidationPipe } from '@nestjs/common';
import { HttpExceptionFilter } from './common/filters/http-exception.filter';
import { AllExceptionFilter } from './common/filters/all-exceptions.filter';
import { ApiKeyGuard } from './common/guards/api-key.guard';
import { TimingInterceptor } from './common/interceptors/timing.interceptor';
import { ResponseWrapInterceptor } from './common/interceptors/response-wrap.interceptor';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.useGlobalGuards(new ApiKeyGuard());

  app.useGlobalInterceptors(
    new TimingInterceptor(),
    new ResponseWrapInterceptor(),
  );
  app.useGlobalPipes(new ValidationPipe({ whitelist: true }));

  app.useGlobalFilters(new AllExceptionFilter());
  app.useGlobalFilters(new HttpExceptionFilter());

  await app.listen(process.env.PORT ?? 3000);
}
void bootstrap();
