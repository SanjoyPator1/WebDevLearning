/**
 * Here are your Resolvers for your Schema. They must match
 * the type definitions in your schema
 */

module.exports = {
  Query: {
    pets(_,{input}, ctx){
      return ctx.models.Pet.findMany(input)
    },
    pet(_,{input}, ctx){
      console.log("Query => pet")
      return ctx.models.Pet.findOne(input)
    }
  },
  Mutation: {
    newPet(_, {input}, ctx){
      return ctx.models.Pet.create(input)
    }
  },
  Pet: {
    owner(pet, _, ctx) {
      //since we have only one user now
      return ctx.models.User.findOne()
    },
    img(pet) {
      const defaultImageUrl = (pet.type === 'DOG'
      ? 'https://placedog.net/300/300'
      : 'http://placekitten.com/300/300')

      const imageData = pet.img ? pet.img : defaultImageUrl
      return imageData
    },
    ownerName(pet, _, ctx) {
      //here the pet is not guaranteed to have owner data 
			//after the above owner resolver is executed
      console.log("PET => name "+ JSON.stringify(pet))
      return "hello"
    }
  },
  User: {
    pets(user, _,ctx){
      console.log("USER => pets")
      return ctx.models.Pet.findMany({user: user.id})
    }
  }
}
