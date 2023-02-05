import { makeStyles, withStyles } from "@material-ui/core/styles";

export const useStyles = makeStyles((theme) => ({
  mainContainer:{
    backgroundColor:"black",
    display:"flex",
    justifyContent:"center",
    alignContent:"center",
    borderRadius:15,
    padding:10,
    margin:10
  },
  innerDivStyle: {
    display: "flex",
    justifyContent: "space-between",
    padding: 15,
    paddingInline: 15,
    alignItems: "center",
    backgroundColor:"#E5E7E9",
    
  },

  alignStyle: {
    alignItems: "center"
  },
  justifyCenterStyle : {
    display:"flex",
    justifyContent:"center",
    alignItems: "center"
  },
  inlinePaddingStyle : {
    paddingInline:10
  },
  buttonContainer : {
    padding: 10
  }
}));
