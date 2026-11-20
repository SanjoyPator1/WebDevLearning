import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { NotesModule } from './notes/notes.module';
import { StatsModule } from './stats/stats.module';

@Module({
  imports: [NotesModule, StatsModule],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
