import React,{useState} from 'react'
import './index.css'

import Navbar from '../../components/Navbar'
import Sidebar from '../../components/Sidebar'
import FilterMainBar from '../../components/FilterMainBar'
import CardContainer from '../../containers/CardContainer'

const Main = () => {

    let[searchQuery, setSearchQuery]=useState("")

  return (
    <div className='Main'>
        <div className='Navbar'>
          <Navbar searchQuery={searchQuery} setSearchQuery={setSearchQuery} />
        </div>
        <div className='BottomMainScreen'>
          <div className='LeftBottomMainScreen'>
            <Sidebar/>
          </div>
          <div className='RightBottomMainScreen'>
            <div className='TopRightBottomMainScreen'>
              <FilterMainBar/>
            </div>
            <div className='DownRightBottomMainScreen'>
              <CardContainer searchQuery={searchQuery} />
            </div>
            
          </div>

        </div>
    </div>
  )
}

export default Main