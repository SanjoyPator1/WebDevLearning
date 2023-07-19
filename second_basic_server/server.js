const { ApolloServer,PubSub } = require('apollo-server')
const gql = require('graphql-tag')

const pubSub = new PubSub()
const NEW_ITEM = 'NEW_ITEM'

const typeDefs = gql`

    type User{
        id: ID!
        error: String!
        username: String!
        createdAt: Int!
    }
    
    type Settings {
        user: User!
        theme: String!
    }

    type Item {
        task: String!
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
        createItem(task: String!): Item!
    }

    type Subscription {
        newItem: Item
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
        },
        createItem(_, {task}) {
            const item = {task}
            pubSub.publish(NEW_ITEM, {newItem: item})
            return item
        }
    },
    Subscription: {
        newItem : {
            subscribe: () => pubSub.asyncIterator(NEW_ITEM)
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
    },
    User : {
        error() {
            throw new Error("User error")
        }
    }
    
}

const server = new ApolloServer({
    typeDefs,
    resolvers,
    context(){
        if(connection) {
            return {...connection.context}
        }
    },
    subscriptions : {
        onConnect(params){

        }
    }
})

server.listen(5000)
    .then(() => {
        console.log('listening on port 5000')
    })
