import { ApolloClient } from "apollo-client";
import { InMemoryCache } from "apollo-cache-inmemory";
import { HttpLink } from "apollo-link-http";
import gql from "graphql-tag";

const typeDefs = gql`
    extend type User {
        age: Int
    }
`

const resolvers = {
    User : {
        age() {
            return 35
        }
    }
}

const link = new HttpLink({ uri: "http://localhost:4000/" });

const cache = new InMemoryCache();

const client = new ApolloClient({
    link,
    cache,
    resolvers,
    typeDefs
});


export default client;
