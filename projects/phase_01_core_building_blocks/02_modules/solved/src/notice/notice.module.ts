import { Module } from '@nestjs/common';
import { NoticeService } from './notice.service.js';

// Not part of this exercise, but read it: NoticeModule deliberately does NOT import
// LoggerModule. It only works because LoggerModule is global (Task 4). That hidden
// dependency is exactly why global modules should be rare.
@Module({
  providers: [NoticeService],
  exports: [NoticeService],
})
export class NoticeModule {}
