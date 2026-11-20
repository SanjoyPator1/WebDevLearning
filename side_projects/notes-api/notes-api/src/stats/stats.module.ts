import { Module } from '@nestjs/common';
import { StatsService } from './stats.service';
import { StatsController } from './stats.controller';
import { NotesModule } from '../notes/notes.module';

@Module({
  imports: [NotesModule],
  providers: [StatsService],
  controllers: [StatsController]
})
export class StatsModule {}
