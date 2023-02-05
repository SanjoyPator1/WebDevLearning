import React from 'react'
import './index.css'

import catalogLogo from '../../assets/SVGimages/catalog.svg'
import playgroundLogo from '../../assets/SVGimages/playground.svg'
import dashboardLogo from '../../assets/SVGimages/dashboard.svg'
import { Typography } from "@material-ui/core";

const Sidebar = () => {
  return (
    <div className='flex-container-sb '>
      <div className='catalog-container shape'>
        <img src={catalogLogo} alt="catalogLogo"/>
        <Typography className='typography'>
          Catalog
        </Typography>
      </div>
      <div className='playground-container shape'>
        <img src={playgroundLogo} alt="playgroundLogo"/>
        <Typography className='typography'>
        Playground
        </Typography>
      </div>
        <div className='dashboard-container shape'>
        <img src={dashboardLogo} alt="dashboardLogo"/>
        <Typography className='typography'>
          Dashboard
        </Typography>
      </div>
    </div>
  )
}

export default Sidebar