import React from 'react';
import './index.css'

import Button from '@material-ui/core/Button';
import { makeStyles } from '@material-ui/core/styles';
import DeleteIcon from '@material-ui/icons/Delete';
import CloudUploadIcon from '@material-ui/icons/CloudUpload';
import KeyboardVoiceIcon from '@material-ui/icons/KeyboardVoice';
import Icon from '@material-ui/core/Icon';
import SaveIcon from '@material-ui/icons/Save';

import ArrowBackSharpIcon from '@material-ui/icons/ArrowBackSharp';
import ArrowForwardSharpIcon from '@material-ui/icons/ArrowForwardSharp';

const useStyles = makeStyles((theme) => ({
    button: {
      margin: theme.spacing(1),
      textTransform:"none",
      width: '114px',
      height: '31px',
      background: '#E7E4E4',
      border: '1px solid rgba(0, 0, 0, 0.25)',
      borderRadius: '5px',
    },
    paginationButtonDesign:{
        width: '31px',
        height: '31px',
        border: '1px solid rgba(0, 0, 0, 0.25)',
        borderRadius: '5px',
        marginInline:'3px'

    }
  }));

const Pagination = ({ postsPerPage, totalPosts, paginate, currentPage }) => {

    const classes = useStyles();

    const pageNumbers = [];

  for (let i = 1; i <= Math.ceil(totalPosts / postsPerPage); i++) {
    pageNumbers.push(i);
  }

  return (
    <div className='pagination--main-container'>
        <div className='pagination-button-container'>
            <Button
                variant="contained"
                color="default"
                className={classes.button}
                startIcon={<ArrowBackSharpIcon />}
                onClick={()=>{
                    if(currentPage!==1){
                        paginate(currentPage-1)
                    }
                }}
            >
                Previous
            </Button>
        </div>
        <div className='numbers-container'>
            {pageNumbers.map(number => (
                <Button variant="contained" className={classes.paginationButtonDesign} href="!#"
                style={{
                    backgroundColor:number===currentPage? '#D04A5C' : 'white',
                    color:number===currentPage?'white' : 'black'
                }}
                onClick={() => {
                    paginate(number)
                }}>
                    {number}
                </Button>
            ))}
        </div>
        <div className='pagination-button-container'>
            <Button
                variant="contained"
                color="default"
                className={classes.button}
                endIcon={<ArrowForwardSharpIcon />}
                onClick={()=>{
                    if(currentPage!==pageNumbers.length){
                        paginate(currentPage+1)
                    }
                }}
            >
                Next
            </Button>
        </div>
    </div>
  );
};

export default Pagination;