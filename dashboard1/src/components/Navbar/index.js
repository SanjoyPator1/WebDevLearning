import React from 'react'
import './index.css'
import AppBar from '@material-ui/core/AppBar';

import logoCompany from  '../../assets/SVGimages/companyLogo.svg'
import DropdownStatus from '../DropdownStatus';
import SearchBarContainer from '../../containers/SearchBarContainer'
import AvatarComponent from '../AvatarComponent';

import Toolbar from '@material-ui/core/Toolbar';

const Navbar = ({searchQuery, setSearchQuery}) => {
  return (
    <React.Fragment>
    <AppBar color="inherit">
        <Toolbar style={{
            justifyContent: "space-between"
        }}>
                <div className='Nv-left'>
                    <div className='TechLogo'>
                        <img src={logoCompany} alt="company logo"/>
                    </div>
                    <div className='St-Dd'>
                        <DropdownStatus/>
                    </div>
                    <div className='Search-Bar'>
                        <SearchBarContainer searchQuery={searchQuery} setSearchQuery={setSearchQuery}/>
                    </div>
                </div>
                <div className='Nv-right'>
                    <AvatarComponent />
                </div>
        </Toolbar>
    </AppBar>
    <Toolbar />
    </React.Fragment>
    )
}

export default Navbar