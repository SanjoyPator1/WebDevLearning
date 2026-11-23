import { ClockService } from '../clock/clock.service.js';

// TODO(1.4) Task 1
// Turn this class into a provider that Nest can build with its dependency.
//   1. Mark it so that Nest treats it as a provider.
//   2. Ask for ClockService in the constructor, as a parameter property.
//   3. stamp(text) returns `${the clock's next tick} ${text}`, for example "tick-1 hello".
// ReportService, next to this file, is finished and does the same: use it as the model.
export class StampService {
  stamp(text: string): string {
    void ClockService; // placeholder so the import is used: remove it when you use ClockService
    throw new Error('TODO(1.4) Task 1: stamp');
  }
}
