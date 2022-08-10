import React from 'react'
import './index.css'
import { makeStyles } from '@material-ui/core/styles';
import { Typography } from "@material-ui/core";
import theme from '../../theme'

import DropdownFilter from '../DropdownFilter'
import gridViewButton from '../../assets/SVGimages/gridViewButton.svg'
import listViewButton from '../../assets/SVGimages/listViewButton.svg'


const useStyles = makeStyles((theme) => ({
    root:{
        width: '179px',
        height: '29px',
        left: '170px',
        top: '127px',
        
        // fontFamily: 'Montserrat',
        fontFamily: 'Poppins, sans-serif',
        fontStyle: 'normal',
        fontSize: '24px',
        lineHeight: '29px',
        
        color: '#6633F2',
        fontWeight: '700',
        margin:'10px'
    }
}))

const FilterMainBar = () => {
    const classes = useStyles(theme);
  return (
    <div className='filter-bar-container'>
        <div className='filter-bar-left'>
            <Typography className={classes.root}>
                Search results
            </Typography>
            <DropdownFilter title='Project'/>
            <DropdownFilter title='Type'/>
        </div>
        <div className='filter-bar-right'>
            <div className='grid distanceDDF'>
                <img src={gridViewButton} alt="gridViewButton"/>
            </div>
            <div className='list distanceDDF'>
                <img src={listViewButton} alt="listViewButton"/>
            
            </div>
        </div>
    </div>
  )
}

export default FilterMainBar