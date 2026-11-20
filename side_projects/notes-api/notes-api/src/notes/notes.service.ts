import { Injectable, NotFoundException } from '@nestjs/common';
import { CreateNoteDto } from './dto/create-note.dto';
import { UpdateNoteDto } from './dto/update-note.dto';
import { Note } from './entities/note.entity';

@Injectable()
export class NotesService {
  private notes: Note[] = []
  private nextId = 1

  create(createNoteDto: CreateNoteDto): Note {
    // build a Note with id: this,nextId++ and dto fields
    // push it into this.notes, then return it

    const note: Note = {
      id: this.nextId++,
      title: createNoteDto.title,
      content: createNoteDto.content
    }

    this.notes.push(note)

    return note
  }

  findAll(): Note[] {
    return this.notes
  }

  findOne(id: number): Note {

    const noteFound = this.notes.find((note) => note.id === id)

    if(!noteFound){
      throw new NotFoundException(`Note not found with ${id}`)
    }

    return noteFound
  }

  update(id: number, updateNoteDto: UpdateNoteDto): Note {
    // reuse this.findOne(id) to get the note
    // copy the new fields onto it with Object.assign(note, updateNoteDto)
    // return the note

    const noteToUpdate = this.notes.find((note) => note.id === id)

    if(!noteToUpdate){
      throw new NotFoundException("Note to update not found")
    }
    
    Object.assign(noteToUpdate, updateNoteDto)
    return noteToUpdate
  }

  remove(id: number): Note {
    // reuse this.findOne(id) so a missing note throws a 404
    // then filter it out: this.notes = this.notes.filter((note) => note.id !== id)
    
    const noteToRemove = this.notes.find((note) => note.id === id)

    if(!noteToRemove){
      throw new NotFoundException("Note to remove not found")
    }

    this.notes = this.notes.filter((note) => note.id !== id)

    return noteToRemove
  }
}
