const { ApolloServer, SchemaDirectiveVisitor } = require('apollo-server')
const {defaultFieldResolver, GraphQLString} = require('graphql')
const typeDefs = require('./typedefs')
const resolvers = require('./resolvers')
const { createToken, getUserFromToken } = require('./auth')
const db = require('./db')

class LogDirective extends SchemaDirectiveVisitor {
  visitFieldDefinition(field) {
      // console.log(field)
      const resolver = field.resolve || defaultFieldResolver
      const {message: schemaMessage} = this.args
      field.args.push({
        type : GraphQLString,
        name: 'message'
      })
      field.resolve = (root, {message, ...rest}, ctx, info) => {
        console.log('⚡ hello : ',message || schemaMessage)
        return resolver.apply(this, root, rest, ctx, info)
      }
  }
}

const server = new ApolloServer({
  typeDefs,
  resolvers,
  schemaDirectives: {
    log: LogDirective
  },
  context({ req, connection }) {
    const context = { ...db }
    if (connection) {
      return { ...context, ...connection.context }
    }
    const token = req.headers.authorization
    const user = getUserFromToken(token)
    return { ...context, user, createToken }
  },
  subscriptions: {
    onConnect(params) {
      const token = params.authToken
      const user = getUserFromToken(token)
      // console.log({user})
      if (!user) {
        throw new Error('Authentication failed on subscriptions')
      }
      return { user }
    }
  }
})

server.listen(4000).then(({ url }) => {
  console.log(`🚀 Server ready at ${url}`)
})
