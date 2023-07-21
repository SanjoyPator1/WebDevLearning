import React, { useState } from "react";
import gql from "graphql-tag";
import { useQuery, useMutation } from "@apollo/react-hooks";
import PetsList from "../components/PetsList";
import NewPetModal from "../components/NewPetModal";
import Loader from "../components/Loader";

const ALL_PETS = gql`
  query AllPets {
    pets {
      id
      name
      type
      img
      owner {
        id
        age @client
      }
    }
  }
`;

const NEW_PET = gql`
  mutation CreateAPet($newPet: NewPetInput!){
    newPet(input: $newPet){
      id
      name
      type
      img
      owner {
        id
        age @client
      }
    }
  }
`

export default function Pets() {
  const [modal, setModal] = useState(false);
  const queryResult = useQuery(ALL_PETS);
  const { data, loading, error } = queryResult || {};

  const [createPet, newPet] = useMutation(NEW_PET, {
    update(cache, { data: { newPet } }) {
      const data = cache.readQuery({ query: ALL_PETS })
      cache.writeQuery({
        query: ALL_PETS,
        data: { pets: [newPet, ...data.pets] }
      })
    }
  })

  console.log({ data })

  const onSubmit = (input) => {
    setModal(false);
    createPet({
      variables: {
        newPet: input
      },
      optimisticResponse: {
        __typename: 'Mutation',
        addPet: {
          __typename: 'Pet', //name of the returned type
          id: Math.floor(Math.random() * 10000) + '',
          name: input.name,
          type: input.type,
          img: 'https://placehold.co/300'
        }
      }
    })
  };

  if (loading) {
    return <Loader />
  }

  if (error || newPet.error) {
    return <p>Error! ....</p>
  }

  console.log(data.pets[0])

  if (modal) {
    return <NewPetModal onSubmit={onSubmit} onCancel={() => setModal(false)} />;
  }

  return (
    <div className="page pets-page">
      <section>
        <div className="row betwee-xs middle-xs">
          <div className="col-xs-10">
            <h1>Pets</h1>
          </div>

          <div className="col-xs-2">
            <button onClick={() => setModal(true)}>new pet</button>
          </div>
        </div>
      </section>
      <section>
        <PetsList pets={data.pets} />
      </section>
    </div>
  );
}
