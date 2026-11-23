import { ItemsService, type Item } from './items.service.js';
import { UpdateItemDto } from './update-item.dto.js';

// TODO(1.3) Task 1
// This class is not a controller yet. Mark it as one, with the route prefix "items", then
// give each method below its route decorator and read its inputs with parameter decorators.
// Use the method signatures as they are.
//
//   GET   /items            list    ?search=an&limit=2  (both optional)
//   GET   /items/:id        findOne
//   POST  /items            create  body: { "name": "durian" }
//   PATCH /items/:id        update  (Task 8)
//
// Query values and route parameters always arrive as strings. Converting them is your job
// here: pipes that do it for you are topic 1.6.
export class ItemsController {
  constructor(private readonly items: ItemsService) {}

  // TODO(1.3) Task 1: GET /items?search=an&limit=2
  list(search?: string, limit?: string): Item[] {
    throw new Error('TODO(1.3) Task 1: list');
  }

  // TODO(1.3) Task 1: GET /items/:id
  findOne(id: string): Item | undefined {
    throw new Error('TODO(1.3) Task 1: findOne');
  }

  // TODO(1.3) Task 1: POST /items, the JSON body has a "name" property
  create(name: string): Item {
    throw new Error('TODO(1.3) Task 1: create');
  }

  // TODO(1.3) Task 8: PATCH /items/:id, the JSON body is described by UpdateItemDto
  update(id: string, dto: UpdateItemDto): Item | undefined {
    throw new Error('TODO(1.3) Task 8: update');
  }
}
