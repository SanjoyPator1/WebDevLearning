const gql = require('graphql-tag')
const {ApolloServer} = require('apollo-server')

const typeDefs = gql`

    """
    comments to be shown in the toolbox
    """

    enum ShoeType {
        JORDAN
        NIKE
        ADIDAS
    }

    type User{
        email: String!
        avatar: String
        friends: [User!]!
    }

    type Shoe {
        brand: ShoeType
        size: Int!
    }

    input ShoesInput {
        brand: ShoeType
        size: Int
    }

    input NewShoeInput {
        brand : ShoeType!
        size: Int!
    }

    type Query {
        me: User!
        shoes(input: ShoesInput): [Shoe]!
    }

    type Mutation{
        newShoe(input: NewShoeInput!) : Shoe!
    }

`
const resolvers = {
    Query : {
        me(){
            return {
                email: 'yoda@masters.com',
                avatar: 'http://www.masters.com',
                friends: []
            }
        },
        shoes(_, {input}){
            return [
                {brand: 'Nike', size: 12},
                {brand: 'Adidas', size: 13},
            ].filter(shoe => shoe.brand === input.brand)
        }
    },
    Mutation : {
        newShoe(_, {input}){
            //for now just return input
            return input
        }
    }
}

const server = new ApolloServer({
    typeDefs,
    resolvers
})

server.listen(5000)
    .then(()=>{
        console.log('listening on port 5000')
    })
