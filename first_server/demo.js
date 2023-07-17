const gql = require('graphql-tag')
const { ApolloServer } = require('apollo-server')

const typeDefs = gql`

    """
    comments to be shown in the toolbox
    """

    
    type User{
        email: String!
        avatar: String
        shoes: [Shoe!]!
    }
    
    enum ShoeType {
        JORDAN
        NIKE
        ADIDAS
    }

    interface Shoe {
        brand: ShoeType
        size: Int!
        user: User!
    }

    type Sneaker implements Shoe {
        brand: ShoeType
        size: Int!
        sport : String!
        user: User!
    }

    type Boot implements Shoe {
        brand: ShoeType
        size: Int!
        hasGrip : Boolean!
        user: User!
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

const user = {
    id: 1,
    email: 'yoda@masters.com',
    avatar: 'http://www.masters.com',
    shoes: []
}

const shoesData =  [
    { brand: 'NIKE', size: 12, sport: 'basketball', user: 1 },
    { brand: 'ADIDAS', size: 13, hasGrip: true , user: 1},
]

const resolvers = {
    Query: {
        me() {
            return {
                id: 1,
                email: 'yoda@masters.com',
                avatar: 'http://www.masters.com',
                shoes: []
            }
        },
        shoes(_, { input }) {
            return shoesData
        }
    },
    Mutation: {
        newShoe(_, { input }) {
            //for now just return input
            return input
        }
    },
    User:{
        shoes(user) {
            //what we will do is :
            //we will use the user.id and go to database then get all the shoes that has this user id
            return shoesData
        }
    },
    Shoe: {
        __resolveType(shoe) {
            if (shoe.sport) return 'Sneaker';
            if (shoe.hasGrip) return 'Boot';
            return null;
        }
    },
    Sneaker:{
        user(shoe){
            return user
        }
    },
    Boot:{
        user(shoe){
            return user
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
