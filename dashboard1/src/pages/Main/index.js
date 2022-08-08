import React,{useState} from 'react'

import Navbar from '../../components/Navbar'

const Main = () => {

    let[searchQuery, setSearchQuery]=useState("")

  return (
    <div className='Main'>
        <Navbar searchQuery={searchQuery} setSearchQuery={setSearchQuery} />
    </div>
  )
}

export default Main