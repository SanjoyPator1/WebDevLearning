import React, {useEffect, useState} from 'react'


import SearchBar from '../../components/SearchBar'

const renderSearchResult=(searchQuery)=>{
    console.log("New search query is ", searchQuery)
}

const SearchBarContainer = ({searchQuery,setSearchQuery}) => {

    useEffect(()=>{
        console.log("search query changed - useEffect triggered")
        renderSearchResult(searchQuery)
    },[searchQuery])

  return (
    <SearchBar searchQuery={searchQuery} setSearchQuery={setSearchQuery}/>
  )
}

export default SearchBarContainer