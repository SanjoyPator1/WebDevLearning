const gql = require('graphql-tag')
const { ApolloServer } = require('apollo-server')

const typeDefs = gql`

    type User{
        id: ID!
        username: String!
        createdAt: Int!
    }
    
    type Settings {
        user: User!
        theme: String!
    }

    input NewSettingsInput {
        user: ID!
        theme: String!
    }

    type Query {
        me: User!
        settings(user: ID!): Settings!
    }

    type Mutation {
        settings(input: NewSettingsInput) : Settings!
    }

    type Subscription {

    }

`

const resolvers = {
    Query: {
        me() {
            return {
                id:'12121',
                username:'coder21',
                createdAt: 123414123
            }
        },
        settings(_, { user }) {
            return {
                user,
                theme:'Light'
            }
        }
    },
    Mutation: {
        settings(_, { input }) {
            //for now just return input
            return input
        }
    },
    Settings: {
        user(){
            return {
                id:'12121',
                username:'coder21',
                createdAt: 123414123
            }
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
