import React from 'react';
import './index.css'

import { makeStyles } from '@material-ui/core/styles';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import Typography from '@material-ui/core/Typography';

import silverBadge from '../../assets/SVGimages/silverBadge.svg'
import bronzeBadge from '../../assets/SVGimages/bronzeBadge.svg'
import goldBadge from '../../assets/SVGimages/goldBadge.svg'

import VisibilityOutlinedIcon from '@material-ui/icons/VisibilityOutlined';

import Checkbox from '@material-ui/core/Checkbox';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import FormControl from '@material-ui/core/FormControl';



const useStyles = makeStyles({
  root: {
    width: '396px',
    height: '363px',

    border: '2px solid #6633F2',
    borderRadius: '5px',
    overflow: 'unset',
  },
  cardContent:{
    padding: '0px',
    height: '100%'
  },
  bullet: {
    display: 'inline-block',
    margin: '0 2px',
    transform: 'scale(0.8)',
  },
  title: {
    fontSize: 14,
  },
  pos: {
    marginBottom: 12,
  },
  cardTitle:{
    //fontFamily: 'Montserrat',
    fontFamily: 'Poppins, sans-serif',
    fontStyle: 'normal',
    fontWeight: '700',
    fontSize: '18px',
    lineHeight: '22px',
    /* identical to box height */

    textAlign: 'center',

    color: '#000000',
  },
  cardBodyKey:{
      fontFamily: 'Poppins, sans-serif',
      fontStyle: 'normal',
      fontWeight: '700',
      fontSize: '14px',
      lineHeight: '17px',
      color: '#000000',
  },
  cardBodyValue:{
    fontFamily: 'Poppins, sans-serif',
    fontStyle: 'normal',
    fontWeight: '600',
    fontSize: '14px',
    color: '#000000',
    opacity: '50%',
    textAlign: "start",

  },
  cardFooterIcon:{
    color: '#D04A5C'
  },
  cardFooterLabel:{
    fontFamily: 'Poppins, sans-serif',
    fontStyle: 'normal',
    fontWeight: '600',
    fontSize: '14px',
    lineHeight: '17px',
    color: '#D04A5C',
  },
  label:{
    fontSize: '14px',
    fontStyle: 'normal',
    fontFamily: 'Poppins, sans-serif',
    fontWeight: '600',
    lineHeight: '17px',
  }
});

export default function CardDashboard({badge, title, project, description, lastModified, owner}) {
  const classes = useStyles();

  let badgeToShow  = goldBadge

  if(badge==="silver"){
    badgeToShow=silverBadge;
  }
  if(badge==="bronze"){
    badgeToShow=bronzeBadge;
  }

  return (
    <Card className={classes.root} variant="outlined">
      <CardContent className={classes.cardContent}>
        <div className='card-dashboard-main-container'>
            <div className='card-dashboard-header'>
                <div className='card-dashboard-badge'>
                    <img className='badgeLogo' src={badgeToShow} alt="badge logo"/>
                </div>
                <div className='card-dashboard-title'>
                    <Typography className={classes.cardTitle}>
                        {title}
                    </Typography>
                </div>
            </div>
            <div className='card-dashboard-body'>
                <div className='card-dashboard-body-container'>
                <div className='card-dashboard-body-row'>
                <div className='card-body-key'>
                    <Typography className={classes.cardBodyKey}>
                        Project : 
                    </Typography>
                </div>
                <div className='card-body-value'>
                    <Typography className={classes.cardBodyValue}>
                        {project}
                    </Typography>
                </div>
            </div>
            <div className='card-dashboard-body-row'>
                <div style={{
                    display: "flex-inline",
                }}>

                    <Typography className={classes.cardBodyValue} style={{
                        textAlign: "start",
                        color: "grey",
                        opacity: "0.8"
                    }}>
                    <Typography className={classes.cardBodyKey} style={{
                        fontWeight: "bold"
                    }}  component="b">Description: </Typography> {description}
                    </Typography>
                </div>
            </div>
            <div className='card-dashboard-body-row'>
                <div className='card-body-key'>
                    <Typography className={classes.cardBodyKey}>
                        Badge : 
                    </Typography>
                </div>
                <div className='card-body-value'>
                    <Typography className={classes.cardBodyValue}>
                        {badge}
                    </Typography>
                </div>
            </div>
            <div className='card-dashboard-body-row'>
                <div className='card-body-key'>
                    <Typography className={classes.cardBodyKey}>
                        Last modified : 
                    </Typography>
                </div>
                <div className='card-body-value'>
                    <Typography className={classes.cardBodyValue}>
                        {lastModified}
                    </Typography>
                </div>
            </div>
            <div className='card-dashboard-body-row'>
                <div className='card-body-key'>
                    <Typography className={classes.cardBodyKey}>
                        Owner : 
                    </Typography>
                </div>
                <div className='card-body-value'>
                    <Typography className={classes.cardBodyValue}>
                        {owner}
                    </Typography>
                </div>
            </div>
                </div>
            </div>
            <hr className='hrdiv'/>
            <div className='footer'>
                <div className='view-div'>
                    <div className='circle-outline'>
                        <VisibilityOutlinedIcon className={classes.cardFooterIcon}/>
                    </div>
                    <Typography className={classes.cardFooterLabel}>
                        View
                    </Typography>
                </div>
                <div className='view-div'>
                    <FormControl component="fieldset">
                        <FormControlLabel
                            value="Select"
                            classes={{
                                label: classes.label
                            }}
                            control={
                                <div className='circle-outline'>
                                    <Checkbox className={classes.cardFooterIcon} />
                                </div>
                                }
                            label="Select"
                            labelPlacement="start"
                            className={classes.cardFooterLabel}
                        />
                    </FormControl>
                </div>
            </div>
        </div>
      </CardContent>
      
    </Card>
  );
}
