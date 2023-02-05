


import React from 'react';
import './index.css'

import InputBase from '@material-ui/core/InputBase';
import { alpha, makeStyles } from '@material-ui/core/styles';
import SearchIcon from '@material-ui/icons/Search';
import ArrowDropDownIcon from '@material-ui/icons/ArrowDropDown';


const useStyles = makeStyles((theme) => ({
  inputRoot: {
    //color: 'inherit',
  },
  inputInput: {
    flex:"1",
  },
}));

export default function SearchBar({setSearchQuery}) {
  const classes = useStyles();

  return (
    <div className="flex-container">
        <div className="icons">
            <div className="search-icon">
              <SearchIcon />
            </div>
            <div className="dd-icon">
              <ArrowDropDownIcon/>
            </div>
        </div>
        <InputBase
          placeholder="Sales project"
         className={classes.inputInput}
          inputProps={{ 'aria-label': 'search' }}
          onChange={event=>{setSearchQuery(event.target.value)}}
        />
    </div>
  );
}