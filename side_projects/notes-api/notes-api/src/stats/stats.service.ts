import { Injectable } from '@nestjs/common';
import { NotesService } from '../notes/notes.service';

@Injectable()
export class StatsService {
  constructor(private readonly notesService: NotesService) {}

  getCount() {
    //return an object with a total field
    // the value comes from findAll on the notes service
    const totalNotes = this.notesService.findAll().length;

    return {
      total: totalNotes,
    };
  }
}
