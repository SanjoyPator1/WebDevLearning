// PLUGINS IMPORTS //
import React, { FC } from "react";
import {
  FormControl,
  FormHelperText,
  InputLabel,
  MenuItem,
  Select
} from "@material-ui/core";
import { useField } from "formik";
import { at } from "lodash";

//radio imports
import Radio from "@material-ui/core/Radio";
import RadioGroup from "@material-ui/core/RadioGroup";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import FormLabel from "@material-ui/core/FormLabel";
// COMPONENTS IMPORTS //

// EXTRA IMPORTS //

/////////////////////////////////////////////////////////////////////////////

interface IPropsType {
  data: Array<{ label: string; value: boolean }>;
  label?: string;
  name: string;
  fullWidth?: boolean;
  FormikProps?: any;
}

const RadioButtonsGroup: FC<IPropsType> = (props) => {
  const { label, data, ...rest } = props;
  const [field, meta, helper] = useField(props);
  const { value: selectedValue } = field;
  const [touched, error] = at(meta, "touched", "error");
  const isError = touched && error && true;
  const { setValue } = helper;

  function renderHelperText() {
    if (isError) {
      return <FormHelperText>{error}</FormHelperText>;
    }
  }

  //   console.log("Radio button props ", field);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    let resValue = false;
    event.target.value === "true" ? (resValue = true) : (resValue = false);
    //   console.log("handle change radio button event", resValue);
    setValue(resValue);
  };

  return (
    <FormControl {...rest} error={isError}>
      <RadioGroup row {...field} value={selectedValue} onChange={handleChange}>
        {data.map((item, index) => (
          <FormControlLabel
            value={item.value}
            control={<Radio />}
            label={item.label}
          />
        ))}
      </RadioGroup>
      {renderHelperText()}
    </FormControl>
  );
};

export default RadioButtonsGroup;
