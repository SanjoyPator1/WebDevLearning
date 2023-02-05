import React from 'react'
import { makeStyles } from '@material-ui/core/styles';
import MenuItem from '@material-ui/core/MenuItem';
import FormControl from '@material-ui/core/FormControl';
import Select from '@material-ui/core/Select';

const useStyles = makeStyles((theme) => ({
    formControl: {
        
    },
    select: {
        width: '289px',
        height: '42px',
        border: '1px solid #140047',
        borderRadius: "10px",
    } 
  }));


const DropdownStatus = () => {

    const classes = useStyles();
    const [status, setStatus] = React.useState("Draft");

  const handleChange = (event) => {
    setStatus(event.target.value);
  };

  return (
    <div>
      <FormControl variant="filled" className={classes.formControl}>
        <Select
          labelId="simple-select-filled-label"
          id="simple-select-filled"
          value={status}
          onChange={handleChange}
          variant="outlined"
          className={classes.select}
        >
          <MenuItem value={"Draft"}>Draft</MenuItem>
          <MenuItem value={"Saved"}>Saved</MenuItem>
        </Select>
      </FormControl>
    </div>
  );
}

export default DropdownStatus