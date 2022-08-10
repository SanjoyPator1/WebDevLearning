


import React from 'react'
import { makeStyles } from '@material-ui/core/styles';
import MenuItem from '@material-ui/core/MenuItem';
import FormControl from '@material-ui/core/FormControl';
import Select from '@material-ui/core/Select';
import InputLabel from '@material-ui/core/InputLabel';

const useStyles = makeStyles((theme) => ({
    formControl: {
        margin: '5px',
    },
    select: {
        width: '225px',
        height: '45px',

        background: '#FFFFFF',
        border: '1px solid rgba(20, 0, 71, 0.25)',
        boxShadow: '0px 0px 4px rgba(0, 0, 0, 0.25)',
        borderRadius: '5px',
    } ,
    menuSelected: {
        
    }
  }));

const ProjectDDlist = ['Project1', 'Project2', 'Project3']
const TypeDDlist = ['Gold', 'Silver', 'Bronze']

const DropdownFilter = ({title}) => {

    let ddData = ['']
    if(title==="Project"){
        
        ddData = ProjectDDlist;
    } else{
        ddData = TypeDDlist;
    }

    const classes = useStyles();
    const [ddfStatus, setddfStatus] = React.useState(ddData[0]);

  const handleChange = (event) => {
    setddfStatus(event.target.value);
  };

  return (
    <div className='ddfMain'>
      <FormControl variant="filled" className={classes.formControl}>
      <InputLabel id="simple-select-filled-label">{title} : </InputLabel>
        <Select
          labelId="simple-select-filled-label"
          id="simple-select-filled"
          value={ddfStatus}
          onChange={handleChange}
          variant="outlined"
          className={classes.select}
        >
          {
            ddData.map((data)=>{
                return(
                    <MenuItem className={classes.menuSelected} value={data}>{data}</MenuItem>
                )
            })
          }
        </Select>
      </FormControl>
    </div>
  );
}

export default DropdownFilter