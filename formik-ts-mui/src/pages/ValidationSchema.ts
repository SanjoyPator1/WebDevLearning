import * as yup from "yup";
import { boolean } from "yup/lib/locale";

const ValidationSchema : any = {
    BasicFormValidationSchema :{
      age: yup.number().required("Required").typeError("A number is required").min(3,"no should be more than 3").max(100,"no should be less than or equal to 100"),
      },
      
};

export default ValidationSchema