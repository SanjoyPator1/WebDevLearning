const gql = require('graphql-tag')
const { ApolloServer } = require('apollo-server')

const typeDefs = gql`

    """
    comments to be shown in the toolbox
    """

    
    type User{
        email: String!
        avatar: String
        friends: [User!]!
    }
    
    enum ShoeType {
        JORDAN
        NIKE
        ADIDAS
    }

    interface Shoe {
        brand: ShoeType
        size: Int!
    }

    type Sneaker implements Shoe {
        brand: ShoeType
        size: Int!
        sport : String!
    }

    type Boot implements Shoe {
        brand: ShoeType
        size: Int!
        hasGrip : Boolean!
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
    Query: {
        me() {
            return {
                email: 'yoda@masters.com',
                avatar: 'http://www.masters.com',
                friends: []
            }
        },
        shoes(_, { input }) {
            return [
                { brand: 'NIKE', size: 12, sport: 'basketball' },
                { brand: 'ADIDAS', size: 13, hasGrip: true },
            ]
        }
    },
    Mutation: {
        newShoe(_, { input }) {
            //for now just return input
            return input
        }
    },
    Shoe: {
        __resolveType(shoe) {
            if (shoe.sport) return 'Sneaker';
            if (shoe.hasGrip) return 'Boot';
            return null;
        }
    }
}

const server = new ApolloServer({
    typeDefs,
    resolvers
})

server.listen(5000)
    .then(() => {
        console.log('listening on port 5000')
    })
