// Task 8: a DTO (data transfer object) describes the shape of a request body.
//
// It is a class and not an interface because of what survives compilation. An interface is
// erased, so for an interface-typed parameter the emitted design:paramtypes entry is plain
// `Object`. A class is a real value, so Nest (and the validation pipes of 1.6 and 3.2) can read
// it from the metadata and find the rules that decorators on its properties would add.
//
// `name` is optional: a PATCH may change only some of the fields.
export class UpdateItemDto {
  name?: string;
}
